import logging
import redis
from app.core.config import config

logger = logging.getLogger(__name__)


class RedisUtil:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisUtil, cls).__new__(cls)
            cls._instance.redis_client = redis.StrictRedis(host=config.REDIS_URL, port=config.REDIS_PORT,
                                                           db=config.REDIS_DB)
        return cls._instance

    def store_event(self, key, value):
        """Store event data in Redis."""
        try:
            self.redis_client.set(key, value)
            logger.info(f"Stored {key} in Redis.")
        except Exception as e:
            logger.error(f"Error storing data in Redis: {e}")

    def get_event(self, key):
        """Retrieve event data from Redis."""
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Error retrieving data from Redis: {e}")
            return None


# Create a singleton instance
redis_util = RedisUtil()
