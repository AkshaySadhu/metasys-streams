import logging

from fastapi import FastAPI

from app.api import root, streaming, subscriptions
from app.db.base import Base
from app.db.databases import db_instance
from app.db.dependency import db_session
from app.services.streaming_manager import StreamingManager
from app.services.token_manager import TokenManager
from app.util.mqtt_utils import mqtt_utils
from app.util.redis_utils import redis_util

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=db_instance.engine)

# Initialize TokenManager and StreamingManager.
token_manager = TokenManager()
streaming_manager = StreamingManager(token_manager=token_manager, db_session=db_session, redis_util=redis_util,
                                     mqtt_utils=mqtt_utils)
app = FastAPI()

# Include API routers.
app.include_router(root.router)
app.include_router(streaming.router, tags=["streaming"])
app.include_router(subscriptions.router, tags=["subscriptions"])


@app.on_event("startup")
def startup_event():
    logger.info("Starting streaming service in background thread...")
    streaming_manager.login()
    streaming_manager.establish_stream()
    events = streaming_manager.sse_client.events()
    streaming_manager.process_hello(events)
    streaming_manager.subscribe_to_all_active_guids()
    streaming_manager.process_events(events)
