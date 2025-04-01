from datetime import datetime, timezone

import requests
import time
import logging
from app.core.config import config

logger = logging.getLogger(__name__)


class TokenManager:
    def __init__(self):
        self.access_token = None
        self.expiry_time = None  # Expected as a Unix timestamp

    def login(self):
        """Login to obtain an access token and expiry time."""
        try:
            url = config.METASYS_SERVER + "/api/v4/login"
            response = requests.post(url, json={
                "username": config.METASYS_USER,
                "password": config.METASYS_PASSWORD
            })
            response.raise_for_status()
            data = response.json()
            self.access_token = data['accessToken']
            dt = datetime.strptime(data['expires'], "%Y-%m-%dT%H:%M:%SZ")
            self.expiry_time = dt.replace(tzinfo=timezone.utc).timestamp()
            logger.info(f"Logged in. Token expires at {self.expiry_time}")
        except requests.RequestException as e:
            logger.error(f"Login failed: {e}")
            raise

    def refresh_token(self):
        """Refresh the token if within 30 minutes of expiry."""
        if self.expiry_time and time.time() >= self.expiry_time - 1800:
            try:
                logger.info("Refreshing token...")
                url = config.METASYS_SERVER + "/api/v4/refreshToken"
                header = {
                    "Authorization": f"Bearer {self.access_token}"
                }
                response = requests.get(url, headers=header)
                response.raise_for_status()
                data = response.json()
                self.access_token = data['accessToken']
                logger.info(f"Refreshed token. Token expires at {self.expiry_time}")
                self.expiry_time = datetime.strptime(data['expires'], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc).timestamp()
                logger.info(f"Refreshed token. Token expires at {self.expiry_time}")

            except Exception as e:
                logger.error(f"Refresh failed: {e}")
