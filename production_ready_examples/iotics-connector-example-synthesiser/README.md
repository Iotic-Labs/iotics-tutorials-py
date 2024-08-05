# Synthesiser Connector

This module provides an example of a Synthesiser Connector that searches for Sensor Twins with the goal of performing computations on the data and sharing the results to the IOTICSpace. Specifically, a Twin Synthesiser with 2 Feeds is created which waits for new data samples to be received. It then periodically computes the average of the received data, along with the Min and Max values. Finally, it shares the synthesised data (Average and Min/Max) via the related Feeds. Overall, this module demonstrates how a Synthesiser Connector can interact with Sensor Twins, receive feed data, process it and share the synthesised data back to an IOTICSpace.

## Components

### synthesiser_connector.py

Defines a **SynthesiserConnector** class that simulates a connector responsible for:
1. Creating the Synthesiser Twin;
2. Searching for the Sensor Twins;
3. Following the Sensor Twins' Feeds;
4. Applying some computation on the feed data received about temperature and humidity;
5. Sharing the synthesised data to the IOTICSpace.

### main.py

Initialises the **DataProcessor** and **SynthesiserConnector** classes and starts the synthesiser connector to listen for feed data from sensor twins and share synthesised data.

## Environment Variables

Set the following environment variables:

- `SYNTHESISER_CONNECTOR_AGENT_KEY_NAME`: Agent Key Name for the this connector
- `SYNTHESISER_CONNECTOR_AGENT_SEED`: Agent Seed for the this connector
- `SYNTHESISER_HOST_URL`: Host URL of where this connector will be connected against

## Connector Dependencies

- **Publisher Connector**: to produce data to be synthesised.

## Commands

Run the following commands from the `production_ready_folder`:

- `make example-synthesiser-run`: Builds and executes the service of the Connector.
- `make example-synthesiser-run-detached`: Same as above, but in detached mode.
- `make example-synthesiser-logs`: Displays the connector's logs.
- `make example-synthesiser-down`: Stops and removes the connector's containers and networks.
