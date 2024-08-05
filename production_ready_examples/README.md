# Production Ready Examples

This folder contains a set of examples of Connectors developed in a robust and efficient fashion to be used in a production environment.

## Connectors Description

### iotics-connector-example-publisher

This module provides an example of a Publisher Connector that simulates the creation of multiple Sensor Twins sharing data about Temperature and Humidity. Each Sensor Twin consists of two Feeds: one for temperature data and the other for humidity data. The semantic descriptions of Twins and Feeds are based on publicly available ontologies.

### iotics-connector-example-historianwriter

This module provides an example of a Follower Connector that searches for Sensor Twins with the goal of storing Feed's data about Temperature and Humidity into a Postgres Database. A Historian Writer Twin is created which waits for new data samples to be received. Overall, this module demonstrates how a follower connector can interact with sensor twins, receive Feed data and process it accordingly.

### iotics-connector-example-synthesiser

This module provides an example of a Synthesiser Connector that searches for Sensor Twins with the goal of performing computations on the data and sharing the results to the IOTICSpace. Specifically, a Twin Synthesiser with 2 Feeds is created which waits for new data samples to be received. It then periodically computes the average of the received data, along with the Min and Max values. Finally, it shares the synthesised data (Average and Min/Max) via the related Feeds. Overall, this module demonstrates how a Synthesiser Connector can interact with Sensor Twins, receive feed data, process it and share the synthesised data back to an IOTICSpace.

### iotics-connector-example-databypass

This module provides an example of using the Data Bypass pattern to grant database access to a user. The Data Bypass Connector creates a Twin with an Input that waits for incoming database requests. Upon receiving a request, the Connector describes the requesting Twin to verify its eligibility for database access. If the requester is allowed, new credentials are generated, and a new user is added to the database. The credentials are then sent back to the requesting Twin's Input, enabling them to access the database.

### iotics-connector-example-historianreader

This module provides an example of requesting database (DB) access and extracting data from it. Specifically, a Historian Reader Twin is created to send DB requests via Input messages to the Data Bypass Twin and receive DB credentials to access and extract data from it.

### iotics-connector-example-common

This module provides a set of Classes and functions to simplify the development of the Connectors.

## Set-up and Execution

Each example is dockerised to facilitate their deployment and execution within a production environment. The execution of the aforementioned Connectors is facilitated through the use of `make` commands.

## Best Practices

When developing your Connector we recommend the following best practices:

- [ ] **Logs between outside IOTICSpace and Connector**. E.g.:
  - "Got data from the API";
  - "Data successfully stored into DB".
- [ ] **Logs between Connector and inside IOTICSpace**. E.g.:
  - "Digital Twin deleted successfully";
  - "A new Twin Identity has been created";
  - "Search Twin operation returned the following Twins".
- [ ] **IOTICS Operations Exception Handling**: handle any exception that can potentially be raised IOTICS wise. E.g.:
  - Failure in Twins operations;
  - Token expiration;
  - IOTICSpace no longer reachable.
- [ ] **Non-IOTICS Operations Exception Handling**: handle anything that can potentially be raised outside IOTICS. E.g.:
  - The Connector's host (PC, Server, etc.) restarts;
  - The data source's API is temporarily unavailable;
  - The DB connection is down.
- [ ] **Comprehensive code documentation**: to enable other developers to understand and debug the code with ease.
- [ ] **Dockerise Connectors**: to be deployed and executed more easily.

## Changelog

Any notable changes made to these examples will be documented in [CHANGELOG.md](./CHANGELOG.md).
