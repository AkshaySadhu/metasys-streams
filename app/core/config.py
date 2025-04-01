import os


class Config:
    METASYS_SERVER = os.getenv("BASE_URL", "https://gt-metasys.org")
    METASYS_USER = os.getenv("METASYS_USER", "username")
    METASYS_PASSWORD = os.getenv("METASYS_PASSWORD", "password")

    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL", "localhost")
    REDIS_PORT = os.getenv("REDIS_PORT", "6379")
    REDIS_DB = os.getenv("REDIS_DB", "0")
    ENABLE_REDIS = os.getenv("ENABLE_REDIS", False)
    REDIS_TTL = int(os.getenv("REDIS_TTL", 86400))

    # MQTT Configuration
    MQTT_URL = os.getenv("MQTT_URL", "localhost")
    MQTT_PORT = os.getenv("MQTT_PORT", "1883")
    MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", 60))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME", "username")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "password")

    # MySQL Configuration
    MYSQL_URL = os.getenv("MYSQL_URL", "mysql+pymysql://user:password@localhost:3306/metasys_db")

    # InfluxDB Configuration
    INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "your-influx-token")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "your-org")
    INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "your-bucket")
    SUBSCRIBE_URL = f'{METASYS_SERVER}/api/v4/objects/{{}}/attributes/presentValue'


config = Config()
