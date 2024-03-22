# Publisher Connector

This module provides an example of a Publisher Connector that simulates the creation of multiple Sensor Twins sharing data about Temperature and Humidity. Each Sensor Twin consists of two Feeds: one for temperature data and the other for humidity data. The semantic descriptions of Twins and Feeds are based on publicly available ontologies.

## data_source.py

Defines a **DataSource** class which provides methods for generating simulated temperature and humidity readings at predefined intervals. These methods encapsulate the logic for generating random values within specified ranges and introduce delays to simulate real-world data acquisition scenarios. The generated readings are returned as dictionaries, which can be utilised by other components of the system, such as the PublisherConnector class for sharing data with Sensor Twins.

## publisher_connector.py

Defines a **PublisherConnector** class responsible for simulating the creation of Sensor Twins and sharing data about temperature and humidity. Upon instantiation, the PublisherConnector object requires a **DataSource** object, which simulates a data source for generating sensor readings. A `start` method orchestrates the entire process by setting up twin structures, creating twins, and initiating data sharing threads. It also ensures that all threads complete their tasks before cleaning up any created Sensor Twins.

## main.py

Initialises a data source (**DataSource**) and a publisher connector (**PublisherConnector**) and starts the process of sharing temperature and humidity data with Sensor Twins.
