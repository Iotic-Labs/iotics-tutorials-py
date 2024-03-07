import logging
import os
from random import randint
from threading import Lock, Thread
from time import sleep

import constants as constant
from identity import Identity
from iotics.lib.grpc.helpers import create_property, create_feed_with_meta, create_value
from iotics.lib.grpc.iotics_api import IoticsApi
from utilities import auto_refresh_token, get_host_endpoints, search_twins

log = logging.getLogger(__name__)


class PublisherConnector:
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
        self._number_of_sensors = int(os.getenv("NUMBER_OF_SENSORS"))
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")
        self._sensors_dict = {}
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
            self._iotics_api.delete_twin(twin_did)
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
            twin_registered_identity = (
                self._iotics_identity.create_twin_with_control_delegation(
                    twin_key_name=f"sensor_{sensor_n+1}"
                )
            )
            twin_did = twin_registered_identity.did
            log.debug("Generated new Twin DID: %s", twin_did)

            twin_label = f"Temperature Sensor {sensor_n+1}"
            twin_properties.append(
                create_property(key=constant.LABEL, value=twin_label, language="en"),
            )
            self._iotics_api.upsert_twin(
                twin_did=twin_did, properties=twin_properties, feeds=feeds
            )
            log.debug("Upsert Twin %s - successful", twin_did)

            self._sensors_dict.update({twin_label: twin_did})
            log.info("Sensor Twin created with DID: %s", twin_did)

    def _make_sensor_reading(self) -> int:
        rand_temperature: int = randint(0, 30)
        log.debug("Generated sensor reading of %d", rand_temperature)

        return rand_temperature

    def _share_data(self):
        while True:
            try:
                for twin_label, twin_did in self._sensors_dict.items():
                    rand_temperature = self._make_sensor_reading()
                    data_to_share: dict = {
                        constant.SENSOR_VALUE_LABEL: rand_temperature
                    }
                    self._iotics_api.share_feed_data(
                        twin_did=twin_did,
                        feed_id=constant.SENSOR_FEED_ID,
                        data=data_to_share,
                    )
                    log.debug(
                        "Shared Feed Data from Twin %s Feed %s - successful",
                        twin_did,
                        constant.SENSOR_FEED_ID,
                    )
                    log.info("Shared %s from Twin %s", data_to_share, twin_label)

                sleep(constant.SENSOR_READING_PERIOD)
            except KeyboardInterrupt:
                break

    def start(self):
        self._create_sensor_twins()
        self._share_data()
