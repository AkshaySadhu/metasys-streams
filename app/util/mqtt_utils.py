import json

from paho.mqtt import client as mqtt
from app.core.config import config


class MQTTUtil:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton pattern: only one instance is created.
        if not cls._instance:
            cls._instance = super(MQTTUtil, cls).__new__(cls)
            # Avoid reinitialization if the instance already exists
            if hasattr(cls, "_initialized") and cls._initialized:
                return

            cls._instance.client = mqtt.Client()
            cls._instance.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
            cls._instance.client.on_connect = cls._instance.on_connect
            cls._instance.client.on_disconnect = cls._instance.on_disconnect

            try:
                cls._instance.client.connect(config.MQTT_URL, config.MQTT_PORT)
                # Start a background network loop to process network traffic
                cls._instance.client.loop_start()
            except Exception as e:
                print(f"Connection failed: {e}")

            cls._instance._initialized = True
        return cls._instance

    def on_connect(self, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print(f"Failed to connect, return code: {rc}")

    def on_disconnect(self):
        print("Disconnected from MQTT Broker")

    def publish(self, topic, payload, qos=0, retain=False):
        """Publish a message to the MQTT broker.

        Args:
            topic (str): The MQTT topic to publish to.
            payload (dict): The message payload as a dictionary.
            qos (int, optional): The Quality of Service level. Defaults to 0.
            retain (bool, optional): Whether the message should be retained by the broker. Defaults to False.
        """
        # Convert payload to JSON string before publishing.
        message = json.dumps(payload)
        result = self.client.publish(topic, payload=message, qos=qos, retain=retain)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("Message published successfully")
        else:
            print(f"Failed to publish message. Error: {result.rc}")


mqtt_utils = MQTTUtil()
