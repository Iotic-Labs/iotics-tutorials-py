# Follower Connector

This module provides an example of a Follower Connector that searches for Sensor Twins with the goal of storing Feed's data about Temperature and Humidity into a Database. A Twin Follower is created which waits for new data samples to be received. Overall, this module demonstrates how a follower connector can interact with sensor twins, receive feed data, and process it accordingly.

## follower_connector.py

Defines a **FollowerConnector** class that simulates a connector responsible for following sensor twins and receiving feed data about temperature and humidity. It defines a method to search for sensor twins based on specific criteria and a method to get feed data from the specified twin and feed. This method continuously listens for new data samples and processes them using the **DataProcessor** class. A `start` method orchestrates the entire process by creating the twin, searching for sensor twins, following their feeds, and cleaning up afterward.

## main.py

Initialises the **DataProcessor** and **FollowerConnector** classes and starts the follower connector to listen for feed data from sensor twins.

## How to access the DB

1. Identity the container id that is in use by postgres:
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
