# Metasys Streaming Service

A background streaming service built with FastAPI that connects to the Johnson Controls Metasys SSE API, processes incoming events, and forwards them to multiple storage and messaging systems.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Running the Service](#running-the-service)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Subscription Management](#subscription-management)
- [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)

## Overview
This service authenticates against a Metasys server, establishes a Server-Sent Events (SSE) connection, and processes live building automation data. Each event is:
1. Parsed and stored in a MySQL database.
2. Forwarded to InfluxDB for time-series analytics.
3. Cached in Redis for quick access to the last event ID.
4. Published over MQTT using the Sparkplug B payload format.

A FastAPI application provides REST endpoints to control streaming and manage subscriptions.

## Features
- **Token Management**: Automatic login and token refresh before expiry
- **SSE Streaming**: Persistent connection to `/api/v4/stream` with keep-alive
- **Event Processing**: Hello handshake, updates, and heartbeat handling
- **Data Storage**:
  - MySQL (via SQLAlchemy ORM)
  - InfluxDB (HTTP API)
  - Redis (last event ID caching)
- **Messaging**: MQTT publishing (Sparkplug B) for downstream consumers
- **Subscription API**: Subscribe/unsubscribe to specific GUIDs at runtime
- **Health Checks**: `/health` and root endpoint for readiness

## Architecture
```
[Metasys SSE] --> [StreamingManager] --> {MySQL, InfluxDB, Redis, MQTT Broker}
                          |
                       FastAPI
                    /start, /stop
    /subscribe/{guid}, /unsubscribe/{guid}
```

- **StreamingManager**: Core class handling login, SSE connection, event parsing, and delegation to storage and messaging.
- **TokenManager**: Logs in to Metasys and refreshes tokens when nearing expiration.
- **EventCrudHandler**: CRUD operations for MySQL via SQLAlchemy.
- **PayloadUtils**: Prepares InfluxDB JSON payloads and Sparkplug B payloads.
- **RedisUtil**: Caches and retrieves the last event ID.
- **MQTTUtil**: Singleton wrapper for Paho MQTT client (connects on startup).

## Prerequisites
- Python 3.9 or higher
- MySQL 5.7+ (or compatible)
- Redis Server
- InfluxDB v2
- MQTT Broker (e.g., Mosquitto)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/metasys-streaming-service.git
   cd metasys-streaming-service
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
Configuration is managed via environment variables. You can create a `.env` file in the project root or export variables directly:

```bash
# Metasys API
BASE_URL=https://gt-metasys.org
METASYS_USER=your_username
METASYS_PASSWORD=your_password

# MySQL (SQLAlchemy URL)
MYSQL_URL=mysql+pymysql://user:password@host:3306/metasys_db

# Redis
enable_REDIS=True # set to False to disable
REDIS_URL=localhost
REDIS_PORT=6379
REDIS_DB=0

# InfluxDB\INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influx_token
INFLUXDB_ORG=your_org
INFLUXDB_BUCKET=your_bucket

# MQTT
MQTT_URL=localhost
MQTT_PORT=1883
MQTT_USERNAME=username
MQTT_PASSWORD=password
```

## Environment Variables
| Variable              | Description                                | Default                      |
|-----------------------|--------------------------------------------|------------------------------|
| `BASE_URL`            | Metasys server base URL                    | `https://gt-metasys.org`     |
| `METASYS_USER`        | Metasys API username                       | `username`                   |
| `METASYS_PASSWORD`    | Metasys API password                       | `password`                   |
| `MYSQL_URL`           | SQLAlchemy compatible MySQL connection URL  | see config.py                |
| `ENABLE_REDIS`        | Enable Redis caching                       | `False`                      |
| `REDIS_URL`           | Redis host                                 | `localhost`                  |
| `REDIS_PORT`          | Redis port                                 | `6379`                       |
| `REDIS_DB`            | Redis database index                       | `0`                          |
| `INFLUXDB_URL`        | InfluxDB HTTP API URL                      | `http://localhost:8086`      |
| `INFLUXDB_TOKEN`      | InfluxDB authentication token              | `your-influx-token`          |
| `INFLUXDB_ORG`        | InfluxDB organization                      | `your-org`                   |
| `INFLUXDB_BUCKET`     | InfluxDB bucket                            | `your-bucket`                |
| `MQTT_URL`            | MQTT broker host                           | `localhost`                  |
| `MQTT_PORT`           | MQTT broker port                           | `1883`                       |
| `MQTT_USERNAME`       | MQTT username                              | `username`                   |
| `MQTT_PASSWORD`       | MQTT password                              | `password`                   |

## Running the Service
1. Ensure all dependencies are running (MySQL, Redis, InfluxDB, MQTT broker).
2. Initialize the database schema:
   ```bash
   python -c "from app.db.base import Base; from app.db.databases import db_instance; Base.metadata.create_all(bind=db_instance.engine)"
   ```
3. Start the FastAPI application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. On startup, the streaming service will begin in a background thread.

## Running the Service

- Startup Event: On FastAPI startup, the startup_event handler in app/main.py is triggered:

```
@app.on_event("startup")
def startup_event():
    token_manager = TokenManager()
    streaming_manager = StreamingManager(
        token_manager=token_manager,
        db_session=db_session,
        redis_util=redis_util,
        mqtt_utils=mqtt_utils
    )
    # Begins SSE streaming in a background thread
    streaming_manager.start_streaming_loop()
```

- StreamingManager Initialization: This call starts a continuous loop that:

  - Logs in to the Metasys API using TokenManager.login(), retrying on failure. This internally calls /api/v4/login API to get the access token and expiry time for the token. This is maintained in a class object for access.

  - Establishes an SSE connection to /api/v4/stream via establish_stream(). This establishes a stream connection and the first event that is received is a server side hello event. This also returns a stream of event which has to be handled by sseclient library. 

  - Processes the initial hello event to set the stream_id (process_hello()). The stream_id is the one which is used to subscribe to the GUIDs which are intended to stream. 

  - Subscribes to all active GUIDs stored in MySQL (subscribe_to_all_active_guids()). To subscribe to the GUID we call this API of the JCI server `/api/v4/objects/{guid}/attributes/presentValue` 

  - Enters an event processing loop (process_events()), which handles token refresh, keep-alive pings, dispatching updates (object.values.update), heartbeat events, and error recovery.

- Resilience: Each stage returns specific status codes on failure (e.g., 1003 for stream errors), causing the loop to retry the corresponding step. Exceptions are logged with stack traces, and a user interrupt (Ctrl+C) will gracefully exit the loop. This can be implemented with a custom logic, hence it is not explaied in detail here.

## API Endpoints

| Method | Path                         | Description                                        |
|--------|------------------------------|----------------------------------------------------|
| GET    | `/`                          | Health message for base service                    |
| GET    | `/health`                    | Health check endpoint                              |
| GET    | `/start`                     | Confirms background streaming is active            |
| GET    | `/stop`                      | Placeholder for stopping streaming (not implemented)|
| POST   | `/subscribe/{guid}`          | Subscribe to updates for a specific GUID           |
| POST   | `/unsubscribe/{guid}`        | Unsubscribe from a specific GUID                   |
| GET    | `/subscriptions`             | List all active subscriptions                      |

## Database Schema
- **events** table:
  - `id`: auto-incremented primary key
  - `eventId`: unique SSE event ID
  - `guid`: object GUID
  - `presentValue`: sensor or point value
  - `event_metadata`: JSON string of condition metadata
  - `stream_id`: SSE stream session ID
  - `timestamp`: insertion timestamp

- **subscriptions** table:
  - `id`: primary key
  - `guid`: subscribed GUID
  - `active`: boolean flag

## Implementation
- Login: Calls the `/api/v4/login` endpoint which returns the 

## Subscription Management
Use the subscription endpoints to add or remove GUIDs at runtime without restarting the service. Subscribed GUIDs are persisted in MySQL and replayed on reconnect.

## Logging
- Python `logging` configured at INFO level by default.
- Errors during streaming, processing, or storage are logged with stack traces.

## Contributing
Contributions are welcome! Please fork the repository and submit pull requests for bug fixes, enhancements, or documentation improvements.

## License
This project is licensed under the MIT License. See `LICENSE` for details.

