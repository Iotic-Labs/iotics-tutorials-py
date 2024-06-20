import csv
import json
import logging
import os
from datetime import datetime
from threading import Lock, Thread
from typing import List

from tqdm import tqdm

import constants as constant
import grpc
from data_processor import DataProcessor
from flask import Flask
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


class FollowerConnector:
    def __init__(self, data_processor: DataProcessor, app: Flask):
        self._data_processor: DataProcessor = data_processor
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._twin_website_did: str = None
        self._threads_list: List[Thread] = None
        self._sensors_data: dict = None
        self._app: Flask = app

        self._initialise()

    def _initialise(self):
        log.debug("Initialising NGN Connector...")
        endpoints = get_host_endpoints(host_url=os.getenv("NGN_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("NGN_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("NGN_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._refresh_token_lock = Lock()

        # Start auto-refreshing token Thread in the background
        Thread(
            target=self._iotics_identity.auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

        # Start Flask App Thread in the background
        th = Thread(target=self._initialise_flask, name="flask")
        th.start()
        self._threads_list = [th]

        self._initialise_sensors_mapping()

    def _initialise_flask(self):
        self._app.run(host="0.0.0.0", port=5000)

    def _parse_sensor_description(self, sensor_description: str):
        description_list = sensor_description.split("_")

        floor_name = room_name = service_type = object_name = measurement_type = (
            "Unknown"
        )

        for description in description_list[1:]:
            description_lower = description.lower()
            if description_lower in [
                floor_name_value.lower()
                for floor_name_value in constant.FLOOR_NAME_VALUES
            ]:
                floor_name = description
            elif description_lower in [
                room_name_value.lower() for room_name_value in constant.ROOM_NAME_VALUES
            ]:
                room_name = description
            elif description_lower in [
                service_type_value.lower()
                for service_type_value in constant.SERVICE_TYPE_VALUES
            ]:
                service_type = description
            elif description_lower in [
                object_name_value.lower()
                for object_name_value in constant.OBJECT_NAME_VALUES
            ]:
                object_name = description
            elif description_lower in [
                measurement_type_value.lower()
                for measurement_type_value in constant.MEASUREMENT_TYPE_VALUES
            ]:
                measurement_type = description

        sensor_dict = {
            "house_number": description_list[0],
            "floor_name": floor_name,
            "room_name": room_name,
            "service_type": service_type,
            "object_name": object_name,
            "measurement_type": measurement_type,
            "description": sensor_description,
            "n_readings_received": 0,
            "last_shared_timestamp_list": [],
        }

        return sensor_dict

    def _initialise_sensors_mapping(self):
        self._sensors_data: dict = {}
        with open("./sensors/sensors_mapping.csv", "r") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                sensor_key = row["sensor_key"]
                sensor_description = row["sensor_description"]
                sensor_dict = self._parse_sensor_description(sensor_description)

                self._sensors_data.update({sensor_key: sensor_dict})

    def _setup_twin_structure(self) -> TwinStructure:
        """Define the Twin structure in terms of Twin's metadata.

        Returns:
            TwinStructure: an object representing the structure of the Twin
        """

        twin_properties = [
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Twin Website", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_CREATED_BY,
                value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
            ),
        ]

        twin_structure = TwinStructure(properties=twin_properties)

        return twin_structure

    def _create_twin(self, twin_structure: TwinStructure):
        """Create the Twin Follower given a Twin Structure.

        Args:
            twin_structure (TwinStructure): Structure of the Twin Follower to create.
        """

        log.info("Creating Twin Website...")

        twin_website_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name="TwinWebsite"
            )
        )
        self._twin_website_did = twin_website_identity.did
        log.debug("Generated new Twin DID: %s", self._twin_website_did)

        retry_on_exception(
            self._iotics_api.upsert_twin,
            "upsert_twin",
            self._refresh_token_lock,
            twin_did=self._twin_website_did,
            properties=twin_structure.properties,
        )

        log.info("Created Twin Follower with DID: %s", self._twin_website_did)

    def _search_sensor_twins(self):
        """Search for the Sensor Twins.

        Returns:
            twins_found_list: list of Twins found by the Search operation.
        """

        log.info("Searching for Sensor Twins...")
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.PROPERTY_KEY_CREATED_BY,
                    value="iotics-connector-cev",
                )
            ],
            response_type="FULL",
        )

        twins_found_list = search_twins(
            search_criteria, self._refresh_token_lock, self._iotics_api, True, 10
        )

        log.info("Found %d Twins based on the search criteria", len(twins_found_list))

        return twins_found_list

    def _decode_data(self, last_shared_data_payload):
        try:
            received_data: dict = json.loads(last_shared_data_payload.feedData.data)
        except json.decoder.JSONDecodeError:
            log.debug("Can't decode data ")
            return {"value": "None"}, "None"

        occurred_at_unix_time = last_shared_data_payload.feedData.occurredAt.seconds
        occurred_at_timestamp = datetime.fromtimestamp(occurred_at_unix_time)

        return received_data, occurred_at_timestamp

    def _get_feed_data(
        self, publisher_twin_did: str, publisher_feed_id: str, sensor_key: str
    ):
        log.debug(
            "Getting Feed data from Twin %s, Feed %s...",
            publisher_twin_did,
            publisher_feed_id,
        )

        unexpected_exception_counter: int = 0

        while True:
            log.debug("Generating a new feed_listener...")
            feed_listener = retry_on_exception(
                self._iotics_api.fetch_interests,
                "fetch_interests",
                self._refresh_token_lock,
                follower_twin_did=self._twin_website_did,
                followed_twin_did=publisher_twin_did,
                followed_feed_id=publisher_feed_id,
                fetch_last_stored=False,
            )

            try:
                for latest_feed_data in feed_listener:
                    log.info(
                        "Received a new data sample from Twin %s Sensor Key %s",
                        publisher_twin_did,
                        sensor_key,
                    )
                    last_shared_data_payload = latest_feed_data.payload

                    received_data, occurred_at_timestamp = self._decode_data(
                        last_shared_data_payload
                    )

                    n_readings_received = self._sensors_data[sensor_key][
                        "n_readings_received"
                    ]
                    last_shared_timestamp_list = self._sensors_data[sensor_key][
                        "last_shared_timestamp_list"
                    ]
                    last_shared_timestamp_list.append(occurred_at_timestamp)

                    self._sensors_data[sensor_key].update(
                        {
                            "last_shared_value": received_data["value"],
                            "last_shared_date": str(occurred_at_timestamp),
                            "last_shared_timestamp_list": last_shared_timestamp_list,
                            "n_readings_received": n_readings_received + 1,
                        }
                    )
            except grpc.RpcError as grpc_ex:
                if not expected_grpc_exception(
                    exception=grpc_ex, operation="feed_listener"
                ):
                    unexpected_exception_counter += 1
            except Exception as gen_ex:
                log.exception("General exception in 'feed_listener': %s", gen_ex)
                unexpected_exception_counter += 1

            if unexpected_exception_counter > constant.RETRYING_ATTEMPTS:
                break

        log.info("Exiting thread...")

    def _get_sensor_key(self, sensor_info):
        sensor_properties = sensor_info.properties
        sensor_key = None

        for sensor_property in sensor_properties:
            if sensor_property.key == constant.PROPERTY_KEY_COMMENT:
                sensor_key = sensor_property.stringLiteralValue.value
                break

        return sensor_key

    def _get_last_shared_value(
        self, publisher_twin_did: str, publisher_feed_id: str, sensor_key: str
    ):
        last_shared_data = retry_on_exception(
            self._iotics_api.fetch_last_stored,
            "fetch_last_stored",
            self._refresh_token_lock,
            follower_twin_did=self._twin_website_did,
            followed_twin_did=publisher_twin_did,
            followed_feed_id=publisher_feed_id,
        )

        last_shared_data_payload = last_shared_data.payload

        received_data, occurred_at_timestamp = self._decode_data(
            last_shared_data_payload
        )

        self._sensors_data[sensor_key].update(
            {
                "last_shared_value": received_data["value"],
                "last_shared_date": str(occurred_at_timestamp),
            }
        )

    def _follow_sensor_twins(self, sensor_twins_list):
        """Create and start a new Thread for each Feed of each Twin included
        in the Sensor Twins List. Then add the thread to the Thread list.

        Args:
            sensor_twins_list: list of Twins found by the Search operation.
        """

        for sensor_twin in tqdm(sensor_twins_list):
            sensor_twin_id = sensor_twin.twinId.id
            sensor_twin_feeds = sensor_twin.feeds
            sensor_key = self._get_sensor_key(sensor_twin)

            for twin_feed in sensor_twin_feeds:
                feed_id = twin_feed.feedId.id

                self._get_last_shared_value(sensor_twin_id, feed_id, sensor_key)

                thread_name = f"{sensor_twin_id}_{feed_id}"

                feed_thread = Thread(
                    target=self._get_feed_data,
                    args=[sensor_twin_id, feed_id, sensor_key],
                    name=thread_name,
                )
                log.debug("Starting new Thread %s...", thread_name)
                feed_thread.start()
                self._threads_list.append(feed_thread)

    def get_sensors_info(self):
        for sensor in self._sensors_data:
            timestamps = self._sensors_data[sensor]["last_shared_timestamp_list"]

            differences = [
                (timestamps[i + 1] - timestamps[i]).total_seconds()
                for i in range(len(timestamps) - 1)
            ]

            try:
                average_difference_seconds = sum(differences) / len(differences)
                average_minutes = round(average_difference_seconds / 60, 2)
            except ZeroDivisionError:
                self._sensors_data[sensor]["avg_sharing_frequency"] = ""
            else:
                self._sensors_data[sensor]["avg_sharing_frequency"] = average_minutes

        return self._sensors_data

    def start(self):
        twin_structure = self._setup_twin_structure()
        self._create_twin(twin_structure)
        sensor_twins_list = self._search_sensor_twins()
        self._follow_sensor_twins(sensor_twins_list)

        for thread in self._threads_list:
            thread.join()
