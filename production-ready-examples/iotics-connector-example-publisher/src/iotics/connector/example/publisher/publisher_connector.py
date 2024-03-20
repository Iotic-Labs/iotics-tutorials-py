import logging
import os
from threading import Lock, Thread
from typing import List

import constants as constant
from data_source import DataSource
from identity import Identity
from iotics.lib.grpc.helpers import (
    create_feed_with_meta,
    create_location,
    create_property,
    create_value,
)
from iotics.lib.grpc.iotics_api import IoticsApi
from twin_structure import TwinStructure
from utilities import auto_refresh_token, get_host_endpoints, retry_on_exception

log = logging.getLogger(__name__)


class PublisherConnector:
    def __init__(self, data_source: DataSource):
        self._data_source: DataSource = data_source
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._threads_list: List[Thread] = None
        self._twins_list: List[TwinStructure] = None

        self._initialise()

    def _initialise(self):
        log.debug("Initialising Publisher Connector...")
        endpoints = get_host_endpoints(host_url=os.getenv("PUBLISHER_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("PUBLISHER_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("PUBLISHER_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._refresh_token_lock = Lock()
        self._threads_list = []
        self._twins_list = []

        # Auto-generate a new token when it expires
        Thread(
            target=auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_identity, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

    def _clear_space(self):
        log.info("Deleting Sensor Twins...")

        for twin_did in self._twins_list:
            retry_on_exception(
                self._iotics_api.delete_twin,
                "delete_twin",
                self._refresh_token_lock,
                twin_did=twin_did,
            )

            log.debug("Deleted Twin DID %s", twin_did)

    def _setup_twin_structure(self) -> TwinStructure:
        twin_properties = [
            create_property(key=constant.TYPE, value=constant.SENSOR, is_uri=True),
            create_property(
                key=constant.COMMENT,
                value="Device that senses info about Temperature and Humidity",
                language="en",
            ),
            create_property(key=constant.CREATED_BY, value=constant.CREATED_BY_NAME),
        ]

        twin_location = create_location(
            lat=constant.LONDON_LAT, lon=constant.LONDON_LON
        )

        # Defining Temperature Feed's Metadata
        temperature_feed_properties = [
            create_property(key=constant.LABEL, value="Temperature", language="en"),
            create_property(
                key=constant.COMMENT,
                value=f"Temperature reading that updates every {constant.TEMPERATURE_READING_PERIOD} seconds",
                language="en",
            ),
        ]
        temperature_feed_values = [
            create_value(
                label=constant.SENSOR_VALUE_LABEL,
                data_type="float",
                unit=constant.CELSIUS_DEGREES,
            ),
        ]
        # Defining Humidity Feed's Metadata
        humidity_feed_properties = [
            create_property(key=constant.LABEL, value="Humidity", language="en"),
            create_property(
                key=constant.COMMENT,
                value=f"Humidity reading that updates every {constant.HUMIDITY_READING_PERIOD} seconds",
                language="en",
            ),
        ]
        humidity_feed_values = [
            create_value(
                label=constant.SENSOR_VALUE_LABEL,
                data_type="integer",
                unit=constant.PERCENT,
            ),
        ]

        feeds_list = [
            create_feed_with_meta(
                feed_id=constant.TEMPERATURE_FEED_ID,
                properties=temperature_feed_properties,
                values=temperature_feed_values,
            ),
            create_feed_with_meta(
                feed_id=constant.HUMIDITY_FEED_ID,
                properties=humidity_feed_properties,
                values=humidity_feed_values,
            ),
        ]

        twin_structure = TwinStructure(
            properties=twin_properties, location=twin_location, feeds_list=feeds_list
        )

        return twin_structure

    def _create_twins(self, twin_structure: TwinStructure):
        log.info("Creating Sensor Twins...")
        for sensor_n in range(constant.NUMBER_OF_SENSORS):
            twin_label = f"Sensor {sensor_n+1}"
            twin_structure.properties.append(
                create_property(key=constant.LABEL, value=twin_label, language="en"),
            )

            twin_registered_identity = (
                self._iotics_identity.create_twin_with_control_delegation(
                    twin_key_name=f"sensor_{sensor_n+1}"
                )
            )
            twin_did: str = twin_registered_identity.did
            log.debug("Generated new Twin DID: %s", twin_did)

            retry_on_exception(
                self._iotics_api.upsert_twin,
                "upsert_twin",
                self._refresh_token_lock,
                twin_did=twin_did,
                location=twin_structure.location,
                properties=twin_structure.properties,
                feeds=twin_structure.feeds_list,
            )

            log.info("%s created with DID: %s", twin_label, twin_did)

            for feed in twin_structure.feeds_list:
                feed_thread = Thread(
                    target=self._share_data,
                    args=[twin_did, feed.id],
                    name=f"{twin_did}_{feed.id}",
                )
                feed_thread.start()
                self._threads_list.append(feed_thread)

            self._twins_list.append(twin_did)

    def _share_data(self, twin_did: str, feed_id: str):
        while True:
            data_type = {
                constant.TEMPERATURE_FEED_ID: self._data_source.make_temperature_reading,
                constant.HUMIDITY_FEED_ID: self._data_source.make_humidity_reading,
            }
            generate_data = data_type.get(feed_id)
            data_to_share = generate_data()

            retry_on_exception(
                self._iotics_api.share_feed_data,
                "share_feed_data",
                self._refresh_token_lock,
                twin_did=twin_did,
                feed_id=feed_id,
                data=data_to_share,
            )

            log.info(
                "Shared %s from Twin DID %s via Feed %s",
                data_to_share,
                twin_did,
                feed_id,
            )

    def start(self):
        twin_structure = self._setup_twin_structure()
        self._create_twins(twin_structure)

        for thread in self._threads_list:
            thread.join()

        self._clear_space()
