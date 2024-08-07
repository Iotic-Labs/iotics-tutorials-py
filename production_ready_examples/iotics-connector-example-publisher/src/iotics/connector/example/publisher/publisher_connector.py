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
from utilities import get_host_endpoints, retry_on_exception

log = logging.getLogger(__name__)


class PublisherConnector:
    def __init__(self, data_source: DataSource):
        """Constructor of a Publisher Connector object.

        Args:
            data_source (DataSource): object simulating a data source.
        """

        self._data_source: DataSource = data_source
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._threads_list: List[Thread] = None

        self._initialise()

    def _initialise(self):
        """Initialise all the variables of this class. It also starts
        an auto refresh token Thread so the IOTICS token is automatically
        regenerated when it expires.
        """

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

        # Start auto-refreshing token Thread in the background
        Thread(
            target=self._iotics_identity.auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

    def _setup_twin_structure(self) -> TwinStructure:
        """Define the Twin structure in terms of Twin's and Feed's metadata.

        Returns:
            TwinStructure: an object representing the structure of the Sensor Twins.
        """

        twin_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.SENSOR, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="Device that senses info about Temperature and Humidity",
                language="en",
            ),
            create_property(
                key=constant.PROPERTY_KEY_CREATED_BY,
                value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
            ),
        ]

        twin_location = create_location(
            lat=constant.LONDON_LAT, lon=constant.LONDON_LON
        )

        # Set-up Temperature Feed's Metadata
        temperature_feed_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.TEMPERATURE, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Temperature", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value=f"Temperature reading that updates every {constant.TEMPERATURE_READING_PERIOD} seconds",
                language="en",
            ),
        ]
        # Set-up Temperature Feed's Value
        temperature_feed_values = [
            create_value(
                label=constant.SENSOR_FEED_VALUE,
                data_type="float",
                unit=constant.CELSIUS_DEGREES,
            ),
        ]

        # Set-up Humidity Feed's Metadata
        humidity_feed_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.HUMIDITY, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Humidity", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value=f"Humidity reading that updates every {constant.HUMIDITY_READING_PERIOD} seconds",
                language="en",
            ),
        ]
        # Set-up Humidity Feed's Value
        humidity_feed_values = [
            create_value(
                label=constant.SENSOR_FEED_VALUE,
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

    def _create_twin(self, twin_structure: TwinStructure, sensor_n: int) -> str:
        """Create a Sensor Twin given a Twin Structure.

        Args:
            twin_structure (TwinStructure): Structure of the Sensor Twin to create.
            sensor_n (int): sensor number to be used as a Twin Key Name.

        Returns:
            int: the Twin DID just created.
        """

        # The Sensor Twin's Label will be dynamically
        # generated according to the Sensor number
        # and added to the list of Twin's Properties
        twin_label = f"Sensor {sensor_n+1}"
        twin_structure.properties.append(
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value=twin_label, language="en"
            ),
        )

        twin_registered_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name=f"sensor_{sensor_n+1}"
            )
        )
        twin_did: str = twin_registered_identity.did
        log.debug("Generated new Twin DID: %s", twin_did)

        retry_on_exception(
            grpc_operation=self._iotics_api.upsert_twin,
            function_name="upsert_twin",
            refresh_token_lock=self._refresh_token_lock,
            twin_did=twin_did,
            location=twin_structure.location,
            properties=twin_structure.properties,
            feeds=twin_structure.feeds_list,
        )

        log.info("%s created with DID: %s", twin_label, twin_did)

        return twin_did

    def _share_data(self, twin_did: str, feed_id: str):
        """This is the entry point of each Thread (i.e.: Feed).
        According to the type of data to generate, either temperature or humidity,
        a new data sample is generated and shared via the specified Twin and Feed.

        Args:
            twin_did (str): the Sensor Twin DID that shares data.
            feed_id (str): the Feed ID from which to share data.
        """

        while True:
            # The following dictionary represents the data generator function to be called
            # based on its key.
            data_type_selection = {
                constant.TEMPERATURE_FEED_ID: self._data_source.make_temperature_reading,
                constant.HUMIDITY_FEED_ID: self._data_source.make_humidity_reading,
            }
            # A specific data generator function will be called according to the Feed ID
            data_generator_function = data_type_selection.get(feed_id)
            data_sample = data_generator_function()

            retry_on_exception(
                grpc_operation=self._iotics_api.share_feed_data,
                function_name="share_feed_data",
                refresh_token_lock=self._refresh_token_lock,
                twin_did=twin_did,
                feed_id=feed_id,
                data=data_sample,
            )

            log.info(
                "Shared %s from Twin DID %s via Feed %s", data_sample, twin_did, feed_id
            )

    def _start_sharing_data(self, twin_structure: TwinStructure, twin_did: str):
        """Each Sensor Twin's Feed will share data asynchronously, so a Thread
        is started for each of them.

        Args:
            twin_structure (TwinStructure): Structure of the Sensor Twin
                used to get info about their Feeds.
            twin_did (str): Twin DID of the Sensor sharing data.
        """

        for feed in twin_structure.feeds_list:
            feed_thread = Thread(
                target=self._share_data,
                args=[twin_did, feed.id],
                name=f"{twin_did}_{feed.id}",
            )
            feed_thread.start()
            self._threads_list.append(feed_thread)

    def start(self):
        """Create the Sensor Twins and share Temperature and Humidity data
        via their Feeds."""

        twin_structure = self._setup_twin_structure()

        log.info("Creating Sensor Twins...")
        for sensor_n in range(constant.NUMBER_OF_SENSORS):
            twin_did = self._create_twin(twin_structure, sensor_n)
            self._start_sharing_data(twin_structure, twin_did)

        for thread in self._threads_list:
            thread.join()
