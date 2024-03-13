from datetime import datetime
import json
import logging
import os
from threading import Lock, Thread
from time import sleep

import constants as constant
import grpc
from data_processor import DataProcessor
from identity import Identity
from iotics.lib.grpc.helpers import create_property
from iotics.lib.grpc.iotics_api import IoticsApi
from utilities import (
    auto_refresh_token,
    get_host_endpoints,
    search_twins,
    log_unexpected_grpc_exceptions_and_sleep,
)

log = logging.getLogger(__name__)


class FollowerConnector:
    def __init__(self, data_processor: DataProcessor):
        self._data_processor: DataProcessor = data_processor
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._twin_follower_did: str = None

    def initialise(self):
        endpoints = get_host_endpoints(host_url=os.getenv("HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("FOLLOWER_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("FOLLOWER_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._refresh_token_lock = Lock()

        # Auto-generate a new token when it expires
        Thread(
            target=auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_identity, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

        self._clear_space()

    def _clear_space(self):
        log.info("Deleting old Follower Twins...")

        # Search for Follower Twins
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.LABEL, value="Twin Follower", language="en"
                ),
                create_property(
                    key=constant.CREATED_BY, value=constant.CREATED_BY_NAME
                ),
            ],
            response_type="FULL",
        )

        twins_found_list = search_twins(
            search_criteria, self._refresh_token_lock, self._iotics_api, False
        )

        twins_deleted_count: int = 0
        for twin in twins_found_list:
            twin_did = twin.twinId.id
            for _ in range(constant.RETRYING_ATTEMPTS):
                try:
                    with self._refresh_token_lock:
                        self._iotics_api.delete_twin(twin_did)
                except grpc.RpcError as ex:
                    self._log_unexpected_grpc_exceptions_and_sleep(
                        exception=ex, operation="delete_twin"
                    )
                else:
                    break

            twins_deleted_count += 1

        log.debug("Deleted %d old Twins", twins_deleted_count)

    def _create_twin_follower(self):
        log.info("Creating Twin Follower...")

        # Define Twin Follower's Metadata
        twin_label: str = "Twin Follower"
        twin_properties = [
            create_property(key=constant.LABEL, value=twin_label, language="en"),
            create_property(
                key=constant.COMMENT,
                value=f"Twin Follower that waits to receive Twin Sensors' data",
                language="en",
            ),
            create_property(key=constant.CREATED_BY, value=constant.CREATED_BY_NAME),
        ]

        # Generate a new Twin Registered Identity for the Twin Follower
        twin_follower_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name="TwinFollower"
            )
        )
        self._twin_follower_did = twin_follower_identity.did
        log.debug("Generated new Twin DID: %s", self._twin_follower_did)

        for _ in range(constant.RETRYING_ATTEMPTS):
            try:
                with self._refresh_token_lock:
                    self._iotics_api.upsert_twin(
                        twin_did=self._twin_follower_did, properties=twin_properties
                    )
            except grpc.RpcError as ex:
                log_unexpected_grpc_exceptions_and_sleep(
                    exception=ex, operation="upsert_twin"
                )
            else:
                break

        log.info("%s created with DID: %s", twin_label, self._twin_follower_did)

    def _search_sensor_twins(self):
        log.info("Searching for Sensor Twins...")
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.CREATED_BY, value=constant.CREATED_BY_NAME
                ),
                create_property(
                    key=constant.TYPE, value=constant.THERMOMETER, is_uri=True
                ),
            ],
            response_type="FULL",
        )

        twins_found_list = search_twins(
            search_criteria, self._refresh_token_lock, self._iotics_api
        )

        log.info("Found %d Twins based on the search criteria", len(twins_found_list))

        return twins_found_list

    def _get_feed_data(self, publisher_twin_did: str, publisher_feed_id: str):
        log.info(
            "Waiting for data from Twin %s, Feed %s...",
            publisher_twin_did,
            publisher_feed_id,
        )
        thread_name = self._generate_thread_name(
            twin_id=publisher_twin_did, feed_id=publisher_feed_id
        )

        get_new_fetch_interest: bool = True

        while True:
            if not get_new_fetch_interest:
                log.debug("'get_new_fetch_interest' set to False. Exiting Thread...")
                break

            for _ in range(constant.RETRYING_ATTEMPTS):
                try:
                    with self._refresh_token_lock:
                        feed_listener = self._iotics_api.fetch_interests(
                            follower_twin_did=self._twin_follower_did,
                            followed_twin_did=publisher_twin_did,
                            followed_feed_id=publisher_feed_id,
                            fetch_last_stored=False,
                        )
                except grpc.RpcError as ex:
                    log_unexpected_grpc_exceptions_and_sleep(
                        exception=ex, operation="fetch_interests"
                    )
                else:
                    break

            try:
                for latest_feed_data in feed_listener:
                    log.debug(
                        "Received a new data sample from Twin %s via Feed %s",
                        publisher_twin_did,
                        publisher_feed_id,
                    )
                    feed_data_payload = latest_feed_data.payload
                    received_data = json.loads(feed_data_payload.feedData.data)
                    occurred_at_unix_time = (
                        feed_data_payload.feedData.occurredAt.seconds
                    )
                    occurred_at_timestamp = str(
                        datetime.fromtimestamp(occurred_at_unix_time)
                    )

                    self._data_processor.print_on_screen(
                        publisher_twin_did,
                        publisher_feed_id,
                        occurred_at_timestamp,
                        received_data,
                    )
            except grpc.RpcError as grpc_ex:
                if (
                    grpc_ex.code() == grpc.StatusCode.CANCELLED
                    and "locally cancelled" in grpc_ex.details().lower()
                ):
                    logging.debug(
                        "Thread %s was requested to be cancelled by this code",
                        thread_name,
                    )
                    get_new_fetch_interest = False
                    break

                log_unexpected_grpc_exceptions_and_sleep(
                    exception=grpc_ex, operation="process_feed_data"
                )
            except Exception as gen_ex:
                log.exception("General exception in '_get_feed_data': %s", gen_ex)
                raise

    def _generate_thread_name(self, twin_id: str, feed_id: str) -> str:
        thread_name: str = f"{twin_id}_{feed_id}"

        return thread_name

    def _follow_sensor_twins(self, sensor_twins_list):
        for sensor_twin in sensor_twins_list:
            sensor_twin_id = sensor_twin.twinId.id
            sensor_twin_feeds = sensor_twin.feeds

            for twin_feed in sensor_twin_feeds:
                feed_id = twin_feed.feedId.id

                thread_name = self._generate_thread_name(
                    twin_id=sensor_twin_id, feed_id=feed_id
                )

                Thread(
                    target=self._get_feed_data,
                    args=[sensor_twin_id, feed_id],
                    name=thread_name,
                ).start()

    def start(self):
        self._create_twin_follower()
        sensor_twins_list = self._search_sensor_twins()
        self._follow_sensor_twins(sensor_twins_list)
