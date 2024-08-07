import logging
import os
from threading import Lock, Thread
from typing import List

import constants as constant
import grpc
from data_processor import DataProcessor
from identity import Identity
from iotics.lib.grpc.helpers import create_property
from iotics.lib.grpc.iotics_api import IoticsApi
from twin_structure import TwinStructure
from utilities import (
    expected_grpc_exception,
    get_host_endpoints,
    retry_on_exception,
    search_twins,
)

log = logging.getLogger(__name__)


class HistorianWriterConnector:
    def __init__(self, data_processor: DataProcessor):
        """Constructor of a Historian Writer Connector object.

        Args:
            data_processor (DataProcessor): object simulating a data processor engine.
        """

        self._data_processor: DataProcessor = data_processor
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._historian_writer_twin_did: str = None
        self._threads_list: List[Thread] = None

        self._initialise()

    def _initialise(self):
        """Initialise all the variables of this class. It also starts
        an auto refresh token Thread so the IOTICS token is automatically
        regenerated when it expires.
        """

        log.debug("Initialising Historian Writer Connector...")
        endpoints = get_host_endpoints(host_url=os.getenv("HISTORIAN_WRITER_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("HISTORIAN_WRITER_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("HISTORIAN_WRITER_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._data_processor.initialise_db_writer(
            db_name=os.getenv("DB_NAME"),
            db_username=os.getenv("DB_USERNAME"),
            db_password=os.getenv("POSTGRES_PASSWORD"),
        )

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
        """Define the Twin structure in terms of Twin's metadata.

        Returns:
            TwinStructure: an object representing the structure of the Twin
        """

        twin_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.DATA_STORE, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Historian Writer", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="Write data to DB about Temperature and Humidity",
                language="en",
            ),
            create_property(
                key=constant.PROPERTY_KEY_CREATED_BY,
                value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
            ),
        ]

        twin_structure = TwinStructure(properties=twin_properties)

        return twin_structure

    def _create_twin(self, twin_structure: TwinStructure):
        """Create the Historian Writer Twin given a Twin Structure.

        Args:
            twin_structure (TwinStructure): Structure of the Historian Writer Twin to create.
        """

        log.info("Creating Historian Writer Twin...")

        twin_identity = self._iotics_identity.create_twin_with_control_delegation(
            twin_key_name="HistorianWriterTwin"
        )
        self._historian_writer_twin_did = twin_identity.did
        log.debug("Generated new Twin DID: %s", self._historian_writer_twin_did)

        retry_on_exception(
            grpc_operation=self._iotics_api.upsert_twin,
            function_name="upsert_twin",
            refresh_token_lock=self._refresh_token_lock,
            twin_did=self._historian_writer_twin_did,
            properties=twin_structure.properties,
        )

        log.info(
            "Created Historian Writer Twin with DID: %s",
            self._historian_writer_twin_did,
        )

    def _search_sensor_twins(self):
        """Search for the Sensor Twins.

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
        """Entry point for each Thread. Within an infinite loop
        get a new feed listener given the info about the Twin and Feed to follow
        alongside the Historian Writer Twin's DID. Wait for new data samples, then process it.
        In case of an expected exception (i.e.: token expired), generate a new
        feed listener and wait again for new data samples.

        Args:
            publisher_twin_did (str): Twin Publisher DID
            publisher_feed_id (str): Twin Publisher's Feed ID
        """

        log.info(
            "Waiting for Feed data from Twin %s, Feed %s...",
            publisher_twin_did,
            publisher_feed_id,
        )

        unexpected_exception_counter: int = 0

        while True:
            log.debug("Generating a new feed_listener...")
            feed_listener = retry_on_exception(
                grpc_operation=self._iotics_api.fetch_interests,
                function_name="fetch_interests",
                refresh_token_lock=self._refresh_token_lock,
                follower_twin_did=self._historian_writer_twin_did,
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

                    # Print data received on screen
                    self._data_processor.print_feed_data_on_screen(
                        publisher_twin_did, publisher_feed_id, latest_feed_data
                    )

                    # Export data receved to DB
                    self._data_processor.export_to_db(
                        publisher_twin_did, publisher_feed_id, latest_feed_data
                    )
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
        in the Sensor Twins List. Then add the thread to the Thread list.

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
        """Create the Historian Writer Twin,
        search for Sensor Twins and follow their Feeds."""

        twin_structure = self._setup_twin_structure()
        self._create_twin(twin_structure)
        sensor_twins_list = self._search_sensor_twins()
        self._follow_sensor_twins(sensor_twins_list)

        for thread in self._threads_list:
            thread.join()
