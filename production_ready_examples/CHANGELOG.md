# Changelog

All notable changes to these examples will be documented in this file.

## 2024-05-15

- Added Postgres DB storage mechanism for Follower Connector.
- Moved `data_source.py` and `data_processor.py` to `iotics-connector-example-common`.
- Moved `auto_refresh_token` method to `identity.py`.

## 2024-03-28

- Fixed logging mechanism to work with Docker and Docker Compose.
- Fixed `retry_on_exception` behaviour when unexpected exceptions occur.
- Added Ontologies for Temperature and Humidity Feeds in Publisher Connector.
