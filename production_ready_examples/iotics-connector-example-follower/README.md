# Follower Connector

This module provides an example of a Follower Connector that searches for Sensor Twins with the purpose of receiving Feed's data about Temperature and Humidity. A Twin Follower is created for this purpose which waits for new data samples to be received. Overall, this module demonstrates how a follower connector can interact with sensor twins, receive feed data, and process it accordingly.

## data_processor.py

Defines a **DataProcessor** class that simulates a data processor. It enables data received from a publisher twin and feed to be printed on the screen.

## follower_connector.py

Defines a **FollowerConnector** class that simulates a connector responsible for following sensor twins and receiving feed data about temperature and humidity. It defines a method to search for sensor twins based on specific criteria and a method to get feed data from the specified twin and feed. This method continuously listens for new data samples and processes them using the **DataProcessor** class. A `start` method orchestrates the entire process by creating the twin, searching for sensor twins, following their feeds, and cleaning up afterward.

## main.py

Initialises the **DataProcessor** and **FollowerConnector** classes and starts the follower connector to listen for feed data from sensor twins.
