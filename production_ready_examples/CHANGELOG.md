# Changelog

All notable changes to these examples will be documented in this file.

## 2024-08-05

- Added **Historian Writer** and **Data Bypass** Connector examples.
- Renamed **Follower Connector** to **Historian Writer** Connector.
- Added `DBReader` and `DBWriter` classes to better manage read and write operations from/to the DB.
- DB credentials moved from `constants.py` to `.env` file
- Added `scope` parameter in `search_twins` method.

## 2024-05-28

- Added **Synthesiser Connector** example.
- Added additional methods to `data_processor.py` used by the Synthesiser Connector.
- Added `use_db` parameter in `DataProcessor` constructor to handle the use of this class with Connectors that don't need the initialisation of `DBManager`.

## 2024-05-15

- Added Postgres DB storage mechanism for Follower Connector.
- Moved `data_source.py` and `data_processor.py` to `iotics-connector-example-common`.
- Moved `auto_refresh_token` method to `identity.py`.

## 2024-03-28

- Fixed logging mechanism to work with Docker and Docker Compose.
- Fixed `retry_on_exception` behaviour when unexpected exceptions occur.
- Added Ontologies for Temperature and Humidity Feeds in Publisher Connector.
