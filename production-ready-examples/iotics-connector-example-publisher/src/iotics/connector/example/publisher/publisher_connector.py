import logging
import os
from threading import Lock, Thread
from time import sleep

import constants as constant
import grpc
from data_source import DataSource
from identity import Identity
from iotics.lib.grpc.helpers import create_feed_with_meta, create_property, create_value
from iotics.lib.grpc.iotics_api import IoticsApi
from utilities import (
    auto_refresh_token,
    get_host_endpoints,
    log_unexpected_grpc_exceptions_and_sleep,
    search_twins,
)

log = logging.getLogger(__name__)


class PublisherConnector:
    def __init__(self, data_source: DataSource):
        self._data_source: DataSource = data_source
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._number_of_sensors: int = None
        self._sensors_dict = {}

    def initialise(self):
        endpoints = get_host_endpoints(host_url=os.getenv("HOST_URL"))
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
        self._number_of_sensors = int(constant.NUMBER_OF_SENSORS)
        self._sensors_dict = {}

        # Auto-generate a new token when it expires
        Thread(
            target=auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_identity, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

        self._clear_space()

    def _clear_space(self):
        log.info("Deleting old Sensor Twins...")

        # Search for Sensor Twins
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.THERMOMETER, is_uri=True
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

    def _create_sensor_twins(self):
        twin_properties = [
            create_property(key=constant.CREATED_BY, value=constant.CREATED_BY_NAME),
            create_property(key=constant.TYPE, value=constant.THERMOMETER, is_uri=True),
        ]
        feed_properties = [
            create_property(
                key=constant.LABEL,
                value="Temperature",
                language="en",
            ),
            create_property(
                key=constant.COMMENT,
                value=f"Temperature reading that updates every {constant.SENSOR_READING_PERIOD} seconds",
                language="en",
            ),
        ]
        feed_values = [
            create_value(
                label=constant.SENSOR_VALUE_LABEL,
                data_type="float",
                unit=constant.CELSIUS_DEGREES,
            ),
        ]
        feeds = [
            create_feed_with_meta(
                feed_id=constant.SENSOR_FEED_ID,
                properties=feed_properties,
                values=feed_values,
            ),
        ]

        for sensor_n in range(self._number_of_sensors):
            twin_label = f"Temperature Sensor {sensor_n+1}"
            twin_properties.append(
                create_property(key=constant.LABEL, value=twin_label, language="en"),
            )

            twin_registered_identity = (
                self._iotics_identity.create_twin_with_control_delegation(
                    twin_key_name=f"sensor_{sensor_n+1}"
                )
            )
            twin_did: str = twin_registered_identity.did
            log.debug("Generated new Twin DID: %s", twin_did)

            for _ in range(constant.RETRYING_ATTEMPTS):
                try:
                    with self._refresh_token_lock:
                        self._iotics_api.upsert_twin(
                            twin_did=twin_did, properties=twin_properties, feeds=feeds
                        )
                except grpc.RpcError as ex:
                    log_unexpected_grpc_exceptions_and_sleep(
                        exception=ex, operation="upsert_twin"
                    )
                else:
                    break

            self._sensors_dict.update({twin_label: twin_did})
            log.info("%s created with DID: %s", twin_label, twin_did)

    def _share_data(self):
        while True:
            try:
                for twin_label, twin_did in self._sensors_dict.items():
                    rand_temperature = self._data_source.make_sensor_reading()
                    data_to_share: dict = {
                        constant.SENSOR_VALUE_LABEL: rand_temperature
                    }
                    for _ in range(constant.RETRYING_ATTEMPTS):
                        try:
                            with self._refresh_token_lock:
                                self._iotics_api.share_feed_data(
                                    twin_did=twin_did,
                                    feed_id=constant.SENSOR_FEED_ID,
                                    data=data_to_share,
                                )
                        except grpc.RpcError as ex:
                            log_unexpected_grpc_exceptions_and_sleep(
                                exception=ex, operation="share_feed_data"
                            )
                        else:
                            break

                    log.info(
                        "Shared %s from Twin %s via Feed %s",
                        data_to_share,
                        twin_label,
                        constant.SENSOR_FEED_ID,
                    )

                sleep(constant.SENSOR_READING_PERIOD)
            except KeyboardInterrupt:
                break

    def start(self):
        self._create_sensor_twins()
        self._share_data()
