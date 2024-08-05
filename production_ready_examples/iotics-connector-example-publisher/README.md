# Publisher Connector

This module provides an example of a Publisher Connector that simulates the creation of multiple Sensor Twins sharing data about Temperature and Humidity. Each Sensor Twin consists of two Feeds: one for temperature data and the other for humidity data. The semantic descriptions of Twins and Feeds are based on publicly available ontologies.

## Components

### publisher_connector.py

Defines a **PublisherConnector** class that simulates a connector responsible for:
1. Creating the Sensor Twins;
2. Sharing data about temperature and humidity.

Upon instantiation, the PublisherConnector object requires a **DataSource** object, which simulates a data source for generating sensor readings. A `start` method orchestrates the entire process by setting up twin structures, creating twins, and initiating data sharing threads. It also ensures that all threads complete their tasks before cleaning up any created Sensor Twins.

### main.py

Initialises a data source (**DataSource**) and a publisher connector (**PublisherConnector**) and starts the process of sharing temperature and humidity data with Sensor Twins.

## Environment Variables

Set the following environment variables:

- `PUBLISHER_CONNECTOR_AGENT_KEY_NAME`: Agent Key Name for the this connector
- `PUBLISHER_CONNECTOR_AGENT_SEED`: Agent Seed for the this connector
- `PUBLISHER_HOST_URL`: Host URL of where this connector will be connected against

## Commands

Run the following commands from the `production_ready_folder`:

- `make example-publisher-run`: Builds and executes the service of the Connector.
- `make example-publisher-run-detached`: Same as above, but in detached mode.
- `make example-publisher-logs`: Displays the connector's logs.
- `make example-publisher-down`: Stops and removes the connector's containers and networks.
