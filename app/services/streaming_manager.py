import json
import logging
import time
import traceback
from datetime import datetime

import requests
from dacite import from_dict
from sseclient import SSEClient

from app.core.config import config
from app.db.CRUDHandle import EventCrudHandler
from app.db.models import Event, Subscriptions
from app.models.EventUpdateObject import EventUpdateObject

logger = logging.getLogger(__name__)


class StreamingManager:
    def __init__(self, token_manager, db_session, redis_util, mqtt_utils):
        """
        :param token_manager: Instance of TokenManager.
        :param storage_service: "redis" or "mysql" (set via environment variable).
        """
        self.token_manager = token_manager
        self.active_subscriptions = {}
        self.db_session = db_session
        self.redis_util = redis_util
        self.mqtt_util = mqtt_utils
        self.session = None
        self.response = None
        self.sse_client = None
        self.events = None
        self.keep_alive_ts = time.time()

    def login(self):
        if not self.token_manager.access_token:
            logger.warning("No access token, retrying login...")
            self.token_manager.login()

    def keep_stream_alive(self):
        if time.time() >= self.keep_alive_ts + 1800:
            url = f"{config.METASYS_SERVER}/api/v4/stream/keepalive"
            headers = {"Authorization": f"Bearer {self.token_manager.access_token}"}
            response = self.session.get(url, headers=headers)
            logger.info(response.json())
            self.keep_alive_ts = time.time()

    def refresh_token_keep_alive(self):
        self.token_manager.refresh_token()
        self.keep_stream_alive()

    def establish_stream(self):
        """Establish a persistent SSE connection using requests and wrap it with ssepy."""
        self.session = requests.Session()
        try:
            url = f"{config.METASYS_SERVER}/api/v4/stream"
            headers = {"Authorization": f"Bearer {self.token_manager.access_token}"}
            self.response = self.session.post(url, headers=headers, stream=True)
            self.response.raise_for_status()
            # Wrap the response with SSEClient from ssepy
            self.sse_client = SSEClient(self.response.raw)
            self.events = self.sse_client.events()
            return
        except Exception as e:
            logger.error(f"Error during streaming connection: {e}")
            traceback.print_exc()
            time.sleep(5)

    def process_hello(self, events):
        try:
            # Iterate over events continuously from the SSE connection.
            event = next(self.events)
            logger.info(f"Received event: {event}")
            match event.event:
                case "hello":
                    self.handle_hello_event(event)
                case _:
                    raise Exception('expected only hello, found something else')
        except Exception as e:
            logger.error(f"Error during processing events: {e}")
            traceback.print_exc()
        return

    def process_events(self, events):
        """Continuously process incoming SSE events using ssepy."""
        try:
            # Iterate over events continuously from the SSE connection.
            for event in self.events:
                logger.info(f"Received event: {event}")
                self.refresh_token_keep_alive()
                match event.event:
                    case "hello":
                        raise Exception('unexpected second hello')
                    case "object.values.update":
                        self.handle_object_update(event)
                    case "object.values.heartbeat":
                        logger.info(event.data + "Event ID: " + event.id)
                if event.id is not None:
                    self.redis_util.store_event("STREAM_LAST_EVENT_ID", event.id)
        except Exception as e:
            logger.error(f"Error during processing events: {e}")
            traceback.print_exc()
        return

    def handle_object_update(self, event):
        """Parse SSE event lines into a JSON object."""
        try:
            event_data = from_dict(data_class=EventUpdateObject, data=json.loads(event.data)[0])
            event_object = Event(guid=event_data.item.id, eventId=event.id, presentValue=event_data.item.presentValue,
                                 event_metadata=str(event_data.condition), stream_id=self.stream_id,
                                 timestamp=datetime.now())
            with self.db_session.session_context() as db:
                crud_session = EventCrudHandler(db)
                crud_session.store_event_mysql(event_object)
                self.dump_to_influx(event_data)
        except Exception as e:
            logger.error(f"Error during processing event: {e}")
            traceback.print_exc()

    def handle_hello_event(self, event):
        self.stream_id = event.data.strip('"')
        logger.info(f"Stream ID set to: {self.stream_id}")
        return

    def subscribe_to_guid(self, guid: str):
        """ Subscribes to the given GUID and returns the response """
        try:

            subscribe_headers = {
                'Authorization': f'Bearer {self.token_manager.access_token}',
                'METASYS-SUBSCRIBE': self.stream_id
            }
            print(config.SUBSCRIBE_URL.format(guid))
            subscribe_response = self.session.get(config.SUBSCRIBE_URL.format(guid), headers=subscribe_headers)

            if subscribe_response.status_code == 200 or subscribe_response.status_code == 204 or subscribe_response.status_code == 202:
                logger.info(f"Successfully subscribed to GUID: {guid}")
            else:
                logger.error(
                    f"Failed to subscribe to GUID {guid}: {subscribe_response.status_code} - {subscribe_response.text}")

            return subscribe_response
        except Exception as e:
            logger.error(f"Error during subscription: {e}")
            traceback.print_exc()
            return None

    def subscribe(self, guid: str):
        """Subscribe to events for a given GUID."""
        if guid not in self.active_subscriptions:
            subscribe_response = self.subscribe_to_guid(guid)
            logger.info(f"Subscribed to GUID: {guid} - Status Code - {subscribe_response.status_code}")
            subscribe_obj = Subscriptions(guid=guid, active=True)
            with self.db_session.session_context() as db:
                crud_session = EventCrudHandler(db)
                crud_session.add_subscription(subscribe_obj)
            return True
        logger.info(f"Already subscribed to GUID: {guid}")
        return False

    def subscribe_to_all_active_guids(self):
        with self.db_session.session_context() as db:
            crud_session = EventCrudHandler(db)
            subscriptions = crud_session.get_subscriptions()
            for guid in subscriptions[::-1]:
                self.subscribe_to_guid(guid)
        logger.info(f"All subscriptions active: {len(subscriptions)}")
        return

    def unsubscribe(self, guid: str):
        """Unsubscribe from events for a given GUID."""
        if guid in self.active_subscriptions:
            del self.active_subscriptions[guid]
            logger.info(f"Unsubscribed from GUID: {guid}")
            return True
        logger.info(f"Not subscribed to GUID: {guid}")
        return False

    def dump_to_influx(self, event: EventUpdateObject):
        """Cron job: Dump stored events from the chosen storage into InfluxDB."""
        try:
            headers = {
                'Authorization': f'Bearer {config.INFLUXDB_TOKEN}',
                'Content-Type': 'application/json'
            }
            print(config.INFLUXDB_URL)
            data = self.prepare_data(event)
            print(data)
            response = self.session.post(config.INFLUXDB_URL, headers=headers, data=data)
            if response.status_code // 100 == 2:
                logger.info(f"InfluxDB response code: {response.status_code}")
            else:
                logger.error(f"Failed to save to influx, Content saved in MySQL Table: {response.status_code}")
        except Exception as e:
            logger.error(f"Error during processing event: {e}")
        return

    def prepare_data(self, event: EventUpdateObject) -> str:
        request = dict()
        request["measurement"] = "Building Data"
        request["presentValue"] = event.item.__dict__.get("presentValue")
        request["guid"] = event.item.__dict__.get("id")
        request["itemReference"] = event.item.__dict__.get("itemReference")
        logger.info(str(request).replace("'", "\""))

        return str(request).replace("'", "\"")
