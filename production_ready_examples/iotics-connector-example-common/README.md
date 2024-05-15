# Common

This module provides a set of Classes and functions to simplify the development of the Connectors.

## constants.py

Provides a list of constant variables used by the Connectors.

## identity.py

Defines a class called **Identity**, which is responsible for managing identities and authentication for interacting with IOTICS. Overall, it facilitates the management of identities and authentication tokens required for interacting with IOTICS, enabling secure communication and access control.

## twin_structure.py

Defines a **TwinStructure** class responsible of simplyfing the definition of Twin's metadata, Feeds and Inputs, facilitating easier retrieval of this information when creating Twins.

## utilities.py

Provides several utility functions for safely executing IOTICS operations and managing token refreshing. Overall, these utility functions ensure robustness and reliability when interacting with the IOTICS, handling errors, token refreshing, and retries gracefully.

## data_processor.py

Defines a **DataProcessor** class that simulates a data processor. It enables data received to be printed on the screen or stored into a DB.

## data_source.py

Defines a **DataSource** class which provides methods for generating simulated temperature and humidity readings at predefined intervals. These methods encapsulate the logic for generating random values within specified ranges and introduce delays to simulate real-world data acquisition scenarios. The generated readings are returned as dictionaries, which can be utilised by other components of the system, such as the PublisherConnector class for sharing data with Sensor Twins.

## db_manager.py

Defines a class called **DBManager** for managing and storing sensor readings in a Postgres database. It leverages SQLAlchemy for ORM (Object-Relational Mapping), threading for concurrent processing, and logging for event tracking.
