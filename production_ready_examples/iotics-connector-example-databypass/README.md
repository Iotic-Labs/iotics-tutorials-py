# Data Bypass Connector

This module provides an example of using the Data Bypass pattern to grant database access to a user. The Data Bypass Connector creates a Twin with an Input that waits for incoming database requests. Upon receiving a request, the Connector describes the requesting Twin to verify its eligibility for database access. If the requester is allowed, new credentials are generated, and a new user is added to the database. The credentials are then sent back to the requesting Twin's Input, enabling them to access the database.

## Components

### databypass_connector.py

Defines a **DataBypassConnector** class that simulates a connector responsible for:
1. Creating a Data Bypass Twin;
2. Waiting for incoming DB requests via Input messages;
3. Granting the requester access to the DB;

It defines a method to wait for incoming Input messages. This method continuously listens for new DB requests and processes them using the **DataProcessor** class. A `start` method orchestrates the entire process by creating the twin, waiting for Input messages and granting DB access.

### main.py

Initialises the **DataProcessor** and **DataBypassConnector** classes and starts the Data Bypass Connector to listen for incoming Input messages.

## Environment Variables

Set the following environment variables:

- `DATABYPASS_CONNECTOR_AGENT_KEY_NAME`: Agent Key Name for the this connector
- `DATABYPASS_CONNECTOR_AGENT_SEED`: Agent Seed for the this connector
- `DATABYPASS_HOST_URL`: Host URL of where this connector will be connected against
- `DB_NAME`: Name of the database (e.g., "iotics_tutorials")
- `DB_USERNAME`: Username to access the database (e.g., "postgres")
- `POSTGRES_PASSWORD`: Password to access the database (e.g., "iotics")
- `POSTGRES_LOG_LEVEL`: Logging level of the Postgres Docker instance (e.g., "warning")

## Commands

Run the following commands from the `production_ready_folder`:

- `make example-databypass-run`: Builds and executes the service of the Connector.
- `make example-databypass-run-detached`: Same as above, but in detached mode.
- `make example-databypass-logs`: Displays the connector's logs.
- `make example-databypass-down`: Stops and removes the connector's containers and networks.
