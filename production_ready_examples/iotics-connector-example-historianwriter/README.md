# Historian Writer Connector

This module provides an example of a Follower Connector that searches for Sensor Twins with the goal of storing Feed's data about Temperature and Humidity into a Postgres Database. A Historian Writer Twin is created which waits for new data samples to be received. Overall, this module demonstrates how a follower connector can interact with sensor twins, receive Feed data and process it accordingly.

## Components

### historian_writer_connector.py

Defines a **HistorianWriterConnector** class that simulates a connector responsible for:
1. Creating a Historian Writer Twin;
2. Searching for the Sensor Twins;
3. Following the Sensor Twins' Feeds;
4. Storing the Feed data received into a DB.

It defines a method to search for sensor twins based on specific criteria and a method to get Feed data from the specified twin and Feed. This method continuously listens for new data samples and processes them using the **DataProcessor** class. A `start` method orchestrates the entire process by creating the twin, searching for sensor twins, following their Feeds, and cleaning up afterward.

### main.py

Initialises the **DataProcessor** and **HistorianWriterConnector** classes and starts the Historian Writer Connector to listen for Feed data from sensor twins.

## Database

In order to store sensor data into a database, a Docker instance of a Postgres database is instantiated and started at the startup of this connector.

Upon initialization of the Historian Writer Connector, the following table and columns are created (derived from the SensorReading class in db_manager.py) to store the data:

- **Table**:
  - **SensorReadings**

- **Columns**:
  - **id**: Column(Integer, primary_key=True)
  - **timestamp**: Column(String(100))
  - **twin_did**: Column(String(50))
  - **feed_id**: Column(String(50))
  - **reading**: Column(Float)

### How to access the DB

1. Identify the container id that is in use by postgres:
```bash
$ docker ps
```
2. Access the container from terminal:
```bash
$ docker exec -it <container_id> bash
```
3. Connect to the DB from within the container:
```bash
$ psql -U postgres -d iotics_tutorials
```
4. Use SQL to interrogate the DB. E.g.:
```sql
$ SELECT * FROM "SensorReadings";
```

## Environment Variables

Set the following environment variables:

- `HISTORIAN_WRITER_CONNECTOR_AGENT_KEY_NAME`: Agent Key Name for the this connector
- `HISTORIAN_WRITER_CONNECTOR_AGENT_SEED`: Agent Seed for the this connector
- `HISTORIAN_WRITER_HOST_URL`: Host URL of where this connector will be connected against
- `DB_NAME`: Name of the database (e.g., "iotics_tutorials")
- `DB_USERNAME`: Username to access the database (e.g., "postgres")
- `POSTGRES_PASSWORD`: Password to access the database (e.g., "iotics")
- `POSTGRES_LOG_LEVEL`: Logging level of the Postgres Docker instance (e.g., "warning")

## Connector Dependencies

- **Publisher Connector**: to produce data to be stored into the DB.

## Commands

Run the following commands from the `production_ready_folder`:

- `make example-historian_writer-run`: Builds and executes the service of the Connector.
- `make example-historian_writer-run-detached`: Same as above, but in detached mode.
- `make example-historian_writer-logs`: Displays the connector's logs.
- `make example-historian_writer-down`: Stops and removes the connector's containers and networks.
