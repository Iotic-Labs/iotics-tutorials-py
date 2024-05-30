# Historian Reader Connector

This module provides an example of requesting database (DB) access and extracting data from it. Specifically, a Historian Reader Twin is created to send DB requests via Input messages to the Data Bypass Twin and receive DB credentials to access and extract data from it.

## Components

### historian_reader_connector.py

Defines a **HistorianReaderConnector** class that simulates a connector responsible for:
1. Creating a Historian Reader Twin;
2. Searching for the Data Bypass Twin;
3. Sending a DB request to the Data Bypass Twin;
4. Waiting for DB credentials to access and extract data from it.

It defines a method to search for the Data Bypass Twin, to send DB requests via Input messages and a method to access the DB upon receiving DB credentials. Once the DB credentials are received, the connector prints all data in the DB initially and any new data received after a specified period of time.

### main.py

Initialises the **DataProcessor** and **HistorianReaderConnector** classes and starts the Historian Reader Connector to send DB requests and wait for DB credentials.

## Environment Variables

Set the following environment variables:

- `HISTORIAN_READER_CONNECTOR_AGENT_KEY_NAME`: Agent Key Name for the this connector
- `HISTORIAN_READER_CONNECTOR_AGENT_SEED`: Agent Seed for the this connector
- `HISTORIAN_READER_HOST_URL`: Host URL of where this connector will be connected against
- `DB_NAME`: Name of the database (e.g., "iotics_tutorials")
- `DB_USERNAME`: Username to access the database (e.g., "postgres")
- `POSTGRES_PASSWORD`: Password to access the database (e.g., "iotics")
- `POSTGRES_LOG_LEVEL`: Logging level of the Postgres Docker instance (e.g., "warning")

## Connector Dependencies

- **Data Bypass Connector**: to ask for DB access and receive DB credentials;
- **Historian Writer Connector**: to store data into the DB;
- **Publisher Connector**: to produce data to be stored into the DB.

## Commands

Run the following commands from the `production_ready_folder`:

- `make example-historian_READER-run`: Builds and executes the service of the Connector.
- `make example-historian_READER-run-detached`: Same as above, but in detached mode.
- `make example-historian_READER-logs`: Displays the connector's logs.
- `make example-historian_READER-down`: Stops and removes the connector's containers and networks.
