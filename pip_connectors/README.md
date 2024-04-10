# PIP Data Connector

This project contains a Connector responsible for integrating PIP Data into the IOTICS Ecosystem.

## Modules Description

### pip-connector-seachange-vesselmovement

This module provides the implementation of a Publisher Connector responsible for creating Vessel Twins and sharing event-based information about arrivals and departures to/from the Portsmouth International Port (PIP).
Each Vessel Twin comprises two Feeds: one for arrival and the other for departure information, both sharing data in an event-based manner based on the Vessel's ATA and ATD respectively.

### pip-connector-seachange-common

This module provides a set of Classes and functions to simplify the development of the Connectors.

## Set-up and Execution

Set all the env variables of the `.env` file within the `docker` directory.
Each module is dockerised to facilitate their deployment and execution within a production environment.

### Linux/MAC OS

The execution of the aforementioned Connector is facilitated through the use of `make` commands from the current directory as follows:

- `make pip-vesselmovement-run`: builds and executes a service of the Vessel Movement Connector;
- `make pip-vesselmovement-run-detached`: same as above, in detached (background) mode;
- `make pip-vesselmovement-logs`: to show the connector's logs when running in detached mode;
- `make pip-vesselmovement-down`: to stop and remove the connector's containers and networks when running in detached mode.

### Windows OS

Within a WSL or a Windows Powershell terminal, use one of the following commands from the current directory:

- `docker compose -f docker/docker-compose.yaml up --build vesselmovement`: to build and execute a service of the Vessel Movement Connector;
- `docker compose -f docker/docker-compose.yaml up --build vesselmovement -d`: same as above, in detached (background) mode;
- `docker compose -f docker/docker-compose.yaml logs vesselmovement -f`: to show the connector's logs when running in detached mode;
- `docker compose -f docker/docker-compose.yaml down vesselmovement`: to stop and remove the connector's containers and networks when running in detached mode.
