import logging
import os
from queue import Queue
from threading import Lock, Thread
from time import sleep
from typing import List

import constants as constant
import grpc
from data_processor import DataProcessor
from identity import Identity
from iotics.lib.grpc.helpers import create_feed_with_meta, create_property, create_value
from iotics.lib.grpc.iotics_api import IoticsApi
from twin_structure import TwinStructure
from utilities import (
    expected_grpc_exception,
    get_host_endpoints,
    retry_on_exception,
    search_twins,
)

log = logging.getLogger(__name__)


class SynthesiserConnector:
    def __init__(self, data_processor: DataProcessor):
        """Constructor of a Synthesiser Connector object.

        Args:
            data_processor (DataProcessor): object simulating a data processor engine.
        """

        self._data_processor: DataProcessor = data_processor
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._twin_synthesiser_did: str = None
        self._threads_list: List[Thread] = None
        self._temperature_data_received_queue: Queue = None
        self._humidity_data_received_queue: Queue = None

        self._initialise()

    def _initialise(self):
        """Initialise all the variables of this class. It also starts
        an auto refresh token Thread so the IOTICS token is automatically
        regenerated when it expires.
        """

        log.debug("Initialising Synthesiser Connector...")
        endpoints = get_host_endpoints(host_url=os.getenv("SYNTHESISER_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("SYNTHESISER_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("SYNTHESISER_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._refresh_token_lock = Lock()
        self._threads_list = []

        # Initialise the queues that will be used to store Feed data received
        self._temperature_data_received_queue = Queue()
        self._humidity_data_received_queue = Queue()

        # Start auto-refreshing token Thread in the background
        Thread(
            target=self._iotics_identity.auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

    def _setup_twin_structure(self) -> TwinStructure:
        """Define the Twin structure in terms of Twin's metadata.

        Returns:
            TwinStructure: an object representing the structure of the Twin
        """

        twin_properties = [
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Twin Synthesiser", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="Twin Synthesiser that receives Twin Sensors' data about "
                "Temperature and Humidity and share their average",
                language="en",
            ),
            create_property(
                key=constant.PROPERTY_KEY_CREATED_BY,
                value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
            ),
        ]

        # Set-up Average Feed's Metadata
        average_feed_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.MEAN_VALUE, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Average", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="Average Temperature and Humidity computed every "
                f"{constant.CALCULATION_PERIOD_SEC} seconds",
                language="en",
            ),
        ]
        # Set-up Average Feed's Values
        average_feed_values = [
            create_value(
                label=constant.AVERAGE_TEMPERATURE_FEED_VALUE,
                data_type="float",
                unit=constant.CELSIUS_DEGREES,
            ),
            create_value(
                label=constant.AVERAGE_HUMIDITY_FEED_VALUE,
                data_type="float",
                unit=constant.PERCENT,
            ),
        ]

        # Set-up Min/Max Feed's Metadata
        min_max_feed_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.MIN_VALUE, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.MAX_VALUE, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Min/Max", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="Min and Max value of Temperature and Humidity computed every "
                f"{constant.CALCULATION_PERIOD_SEC} seconds",
                language="en",
            ),
        ]
        # Set-up Min/Max Feed's Values
        min_max_feed_values = [
            create_value(
                label=constant.MIN_TEMPERATURE_FEED_VALUE,
                data_type="float",
                unit=constant.CELSIUS_DEGREES,
            ),
            create_value(
                label=constant.MAX_TEMPERATURE_FEED_VALUE,
                data_type="float",
                unit=constant.CELSIUS_DEGREES,
            ),
            create_value(
                label=constant.MIN_HUMIDITY_FEED_VALUE,
                data_type="float",
                unit=constant.PERCENT,
            ),
            create_value(
                label=constant.MAX_HUMIDITY_FEED_VALUE,
                data_type="float",
                unit=constant.PERCENT,
            ),
        ]

        feeds_list = [
            create_feed_with_meta(
                feed_id=constant.AVERAGE_FEED_ID,
                properties=average_feed_properties,
                values=average_feed_values,
            ),
            create_feed_with_meta(
                feed_id=constant.MIN_MAX_FEED_ID,
                properties=min_max_feed_properties,
                values=min_max_feed_values,
            ),
        ]

        twin_structure = TwinStructure(
            properties=twin_properties, feeds_list=feeds_list
        )

        return twin_structure

    def _create_twin(self, twin_structure: TwinStructure):
        """Create the Twin Synthesiser given a Twin Structure.

        Args:
            twin_structure (TwinStructure): Structure of the Twin Synthesiser to create.
        """

        log.info("Creating Twin Synthesiser...")

        twin_synthesiser_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name="TwinSynthesiser"
            )
        )
        self._twin_synthesiser_did = twin_synthesiser_identity.did
        log.debug("Generated new Twin DID: %s", self._twin_synthesiser_did)

        retry_on_exception(
            grpc_operation=self._iotics_api.upsert_twin,
            function_name="upsert_twin",
            refresh_token_lock=self._refresh_token_lock,
            twin_did=self._twin_synthesiser_did,
            properties=twin_structure.properties,
            feeds=twin_structure.feeds_list,
        )

        log.info("Created Twin Synthesiser with DID: %s", self._twin_synthesiser_did)

    def _share_average_data(
        self, temperature_data_list: List[float], humidity_data_list: List[float]
    ):
        """Compute the average value and share data via the related Feed.

        Args:
            temperature_data_list (List[float]): list of temperature values received.
            humidity_data_list (List[float]): list of humidity values received.
        """

        # Compute the average value of Temperature and Humidity data
        average_temperature_data = self._data_processor.compute_average(
            temperature_data_list
        )
        average_humidity_data = self._data_processor.compute_average(humidity_data_list)

        # Prepare the dictionary to share via the related Feed
        average_feed_data_to_share = {
            constant.AVERAGE_TEMPERATURE_FEED_VALUE: average_temperature_data,
            constant.AVERAGE_HUMIDITY_FEED_VALUE: average_humidity_data,
        }

        retry_on_exception(
            grpc_operation=self._iotics_api.share_feed_data,
            function_name="share_feed_data",
            refresh_token_lock=self._refresh_token_lock,
            twin_did=self._twin_synthesiser_did,
            feed_id=constant.AVERAGE_FEED_ID,
            data=average_feed_data_to_share,
        )

        log.info(
            "Shared %s via Feed %s",
            average_feed_data_to_share,
            constant.AVERAGE_FEED_ID,
        )

    def _share_min_max_data(
        self, temperature_data_list: List[float], humidity_data_list: List[float]
    ):
        """Compute Min and Max values and share data via the related Feed.

        Args:
            temperature_data_list (List[float]): list of temperature values received.
            humidity_data_list (List[float]): list of humidity values received.
        """

        # Compute Min and Max values of Temperature and Humidity data
        min_temperature, max_temperature = self._data_processor.get_min_max(
            temperature_data_list
        )
        min_humidity, max_humidity = self._data_processor.get_min_max(
            humidity_data_list
        )

        # Prepare the dictionary to share via the related Feed
        min_max_data_to_share = {
            constant.MIN_TEMPERATURE_FEED_VALUE: min_temperature,
            constant.MAX_TEMPERATURE_FEED_VALUE: max_temperature,
            constant.MIN_HUMIDITY_FEED_VALUE: min_humidity,
            constant.MAX_HUMIDITY_FEED_VALUE: max_humidity,
        }

        retry_on_exception(
            grpc_operation=self._iotics_api.share_feed_data,
            function_name="share_feed_data",
            refresh_token_lock=self._refresh_token_lock,
            twin_did=self._twin_synthesiser_did,
            feed_id=constant.MIN_MAX_FEED_ID,
            data=min_max_data_to_share,
        )

        log.info(
            "Shared %s via Feed %s", min_max_data_to_share, constant.MIN_MAX_FEED_ID
        )

    def _share_synthesised_data(self):
        """Periodically empties the temperature and humidity queues, converts them into lists,
        and performs calculations to compute the average, minimum, and maximum values.
        The results are then shared through the appropriate methods.
        """

        while True:
            sleep(constant.CALCULATION_PERIOD_SEC)
            log.debug("Making computation...")

            # Convert Temperature queue into a List
            temperature_data_list = self._data_processor.get_list_of_items(
                self._temperature_data_received_queue
            )
            # Convert Humidity queue into a List
            humidity_data_list = self._data_processor.get_list_of_items(
                self._humidity_data_received_queue
            )

            if temperature_data_list and humidity_data_list:
                self._share_average_data(temperature_data_list, humidity_data_list)
                self._share_min_max_data(temperature_data_list, humidity_data_list)
            else:
                log.info(
                    "No data was received over the last %s seconds",
                    constant.CALCULATION_PERIOD_SEC,
                )

    def _search_sensor_twins(self):
        """Search for the Sensor Twins. Keep retrying if not found.

        Returns:
            twins_found_list: list of Twins found by the Search operation.
        """

        log.info("Searching for Sensor Twins...")
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.PROPERTY_KEY_TYPE, value=constant.SENSOR, is_uri=True
                ),
                create_property(
                    key=constant.PROPERTY_KEY_CREATED_BY,
                    value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
                ),
            ],
            response_type="FULL",
        )

        twins_found_list = search_twins(
            search_criteria=search_criteria,
            refresh_token_lock=self._refresh_token_lock,
            iotics_api=self._iotics_api,
            keep_searching=True,
        )

        log.info("Found %d Twins based on the search criteria", len(twins_found_list))

        return twins_found_list

    def _get_feed_data(self, publisher_twin_did: str, publisher_feed_id: str):
        """Entry point for each Follower Thread. Within an infinite loop
        get a new feed listener given the info about the Twin and Feed to follow
        alongside the Twin Synthesiser's DID. Wait for new data samples, then add it
        to the related queue (either Temperature or Humidity according to the Feed ID).
        In case of an expected exception (i.e.: token expired), generate a new
        feed listener and wait again for new data samples.

        Args:
            publisher_twin_did (str): Twin Publisher DID
            publisher_feed_id (str): Twin Publisher's Feed ID
        """

        log.info(
            "Getting Feed data from Twin %s, Feed %s...",
            publisher_twin_did,
            publisher_feed_id,
        )

        unexpected_exception_counter: int = 0

        # Dictionary used to select the queue where to put the items received
        data_received_queue_selection = {
            constant.TEMPERATURE_FEED_ID: self._temperature_data_received_queue,
            constant.HUMIDITY_FEED_ID: self._humidity_data_received_queue,
        }
        # Select the specific queue according to the Feed ID
        data_received_queue: Queue = data_received_queue_selection.get(
            publisher_feed_id
        )

        while True:
            log.debug("Generating a new feed_listener...")
            feed_listener = retry_on_exception(
                grpc_operation=self._iotics_api.fetch_interests,
                function_name="fetch_interests",
                refresh_token_lock=self._refresh_token_lock,
                follower_twin_did=self._twin_synthesiser_did,
                followed_twin_did=publisher_twin_did,
                followed_feed_id=publisher_feed_id,
                # 'fetch_last_stored' is set to False
                # otherwise at any new 'feed_listener' generated
                # (i.e.: any time the token expires)
                # we will get the last shared value.
                fetch_last_stored=False,
            )

            try:
                for latest_feed_data in feed_listener:
                    log.debug(
                        "Received a new data sample from Twin %s via Feed %s",
                        publisher_twin_did,
                        publisher_feed_id,
                    )

                    # Add item to the queue
                    data_received_queue.put(latest_feed_data)
            except grpc.RpcError as grpc_ex:
                # Any time the token expires, an expected gRPC exception is raised
                # and a new 'feed_listener' object needs to be generated.
                if not expected_grpc_exception(
                    exception=grpc_ex, operation="feed_listener"
                ):
                    unexpected_exception_counter += 1
            except Exception as gen_ex:
                log.exception("General exception in 'feed_listener': %s", gen_ex)
                unexpected_exception_counter += 1

            if unexpected_exception_counter > constant.RETRYING_ATTEMPTS:
                break

        log.debug("Exiting thread...")

    def _follow_sensor_twins(self, sensor_twins_list):
        """Create and start a new Thread for each Feed of each Twin included
        in the Sensor Twins List to wait and process Feed data.
        Then add the thread to the Thread list.

        Args:
            sensor_twins_list: list of Twins found by the Search operation.
        """

        for sensor_twin in sensor_twins_list:
            sensor_twin_id = sensor_twin.twinId.id
            sensor_twin_feeds = sensor_twin.feeds

            for twin_feed in sensor_twin_feeds:
                feed_id = twin_feed.feedId.id

                thread_name = f"{sensor_twin_id}_{feed_id}"

                feed_thread = Thread(
                    target=self._get_feed_data,
                    args=[sensor_twin_id, feed_id],
                    name=thread_name,
                )
                log.debug("Starting new Thread %s...", thread_name)
                feed_thread.start()
                self._threads_list.append(feed_thread)

    def start(self):
        """Create the Twin Synthesiser, search for Sensor Twins and follow their Feeds.
        When a new data sample is received, make some computation and share the data."""

        twin_structure = self._setup_twin_structure()
        self._create_twin(twin_structure)
        sensor_twins_list = self._search_sensor_twins()
        self._follow_sensor_twins(sensor_twins_list)
        self._share_synthesised_data()

        for thread in self._threads_list:
            thread.join()
