import logging
import random
import sys
import threading
from time import sleep
from typing import List

from helpers.constants import (
    PROPERTY_KEY_COLOR,
    PROPERTY_KEY_COMMENT,
    PROPERTY_KEY_CREATED_BY,
    PROPERTY_KEY_FROM_MODEL,
    PROPERTY_KEY_HOST_ALLOW_LIST,
    PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_SPACE_NAME,
    PROPERTY_KEY_TYPE,
    PROPERTY_VALUE_ALLOW_ALL,
    PROPERTY_VALUE_MODEL,
    UNIT_DEGREE_CELSIUS,
)
from helpers.identity import Identity
from helpers.utilities import auto_refresh_token_grpc, get_host_endpoints
from iotics.api.common_pb2 import GeoLocation, Property
from iotics.lib.grpc.helpers import (
    create_feed_with_meta,
    create_location,
    create_property,
    create_value,
)
from iotics.lib.grpc.iotics_api import IoticsApi as IOTICSviagRPC

HOST_URL = ""
USER_KEY_NAME = ""
USER_SEED = ""
AGENT_KEY_NAME = ""
AGENT_SEED = ""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class PublisherConnectorGrpc:
    def __init__(self):
        self._identity: Identity = None
        self._host_id: str = None
        self._iotics_api: IOTICSviagRPC = None

        self._setup()

    def _setup(self):
        endpoints = get_host_endpoints(host_url=HOST_URL)
        self._identity = Identity(
            resolver_url=endpoints["resolver"],
            grpc_endpoint=endpoints["grpc"],
            user_key_name=USER_KEY_NAME,
            user_seed=USER_SEED,
            agent_key_name=AGENT_KEY_NAME,
            agent_seed=AGENT_SEED,
        )
        self._iotics_api = IOTICSviagRPC(auth=self._identity)

        threading.Thread(
            target=auto_refresh_token_grpc,
            args=(
                self._identity,
                self._iotics_api,
            ),
            daemon=True,
        ).start()

    def create_new_twin(
        self,
        twin_key_name: str,
        properties: List[Property],
        feeds: List[dict] = None,
        location: GeoLocation = None,
    ) -> str:
        twin_identity = self._identity.create_twin_with_control_delegation(
            twin_key_name=twin_key_name
        )

        twin_did = twin_identity.did

        resp = self._iotics_api.upsert_twin(
            twin_did=twin_did, location=location, properties=properties, feeds=feeds
        )
        if resp:
            logging.info("Twin %s upserted", twin_did)

        return twin_did

    def share_random_data(self, twin_from_model_did_list: List[str]):
        for twin_from_model_did in twin_from_model_did_list:
            data_to_share = {"reading": random.randint(10, 31)}
            self._iotics_api.share_feed_data(
                twin_did=twin_from_model_did,
                feed_id="temperature",
                data=data_to_share,
            )

            logging.info("Shared %s from Twin %s", data_to_share, twin_from_model_did)


def main():
    publisher = PublisherConnectorGrpc()

    # Create Twin Model
    twin_model_did = publisher.create_new_twin(
        twin_key_name="SensorTwinModel",
        properties=[
            create_property(
                key=PROPERTY_KEY_TYPE, value=PROPERTY_VALUE_MODEL, is_uri=True
            ),
            create_property(
                key=PROPERTY_KEY_LABEL,
                value="Temperature Sensor Model",
                language="en",
            ),
            create_property(
                key=PROPERTY_KEY_COMMENT,
                value="Model of a Temperature Sensor Twin",
                language="en",
            ),
            create_property(
                key=PROPERTY_KEY_SPACE_NAME, value="Replace with Space Name"
            ),
            create_property(key=PROPERTY_KEY_COLOR, value="#9aceff"),
            create_property(
                key=PROPERTY_KEY_CREATED_BY, value="Replace with your Name"
            ),
            create_property(
                key="https://data.iotics.com/app#defines",
                value="https://saref.etsi.org/core/TemperatureSensor",
                is_uri=True,
            ),
            create_property(
                key="https://saref.etsi.org/core/hasModel", value="SET-LATER"
            ),
        ],
        feeds=[
            create_feed_with_meta(
                feed_id="temperature",
                properties=[
                    create_property(
                        key=PROPERTY_KEY_LABEL, value="Temperature", language="en"
                    ),
                    create_property(
                        key=PROPERTY_KEY_COMMENT,
                        value="Random Temperature",
                        language="en",
                    ),
                ],
                values=[
                    create_value(
                        label="reading",
                        comment="Temperature in degrees Celsius",
                        unit=UNIT_DEGREE_CELSIUS,
                        data_type="integer",
                    )
                ],
            )
        ],
    )

    # Create 3 Twins from Model
    twin_from_model_did_list = []
    for temp_sensor in range(3):
        twin_from_model_did = publisher.create_new_twin(
            twin_key_name=f"SensorTwin{temp_sensor}",
            properties=[
                create_property(
                    key=PROPERTY_KEY_FROM_MODEL,
                    value=twin_model_did,
                    is_uri=True,
                ),
                create_property(
                    key=PROPERTY_KEY_LABEL,
                    value=f"Temperature Sensor Twin {temp_sensor+1}",
                    language="en",
                ),
                create_property(
                    key=PROPERTY_KEY_COMMENT,
                    value=f"Temperature Sensor Twin {temp_sensor+1} that shares random temperature data",
                    language="en",
                ),
                create_property(
                    key=PROPERTY_KEY_SPACE_NAME, value="Replace with Space Name"
                ),
                create_property(key=PROPERTY_KEY_COLOR, value="#9aceff"),
                create_property(
                    key=PROPERTY_KEY_CREATED_BY, value="Replace with your Name"
                ),
                create_property(
                    key="https://data.iotics.com/app#defines",
                    value="https://saref.etsi.org/core/TemperatureSensor",
                    is_uri=True,
                ),
                create_property(
                    key="https://saref.etsi.org/core/hasModel", value="T1234"
                ),
                create_property(
                    key=PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
                    value=PROPERTY_VALUE_ALLOW_ALL,
                    is_uri=True,
                ),
                create_property(
                    key=PROPERTY_KEY_HOST_ALLOW_LIST,
                    value=PROPERTY_VALUE_ALLOW_ALL,
                    is_uri=True,
                ),
            ],
            feeds=[
                create_feed_with_meta(
                    feed_id="temperature",
                    properties=[
                        create_property(
                            key=PROPERTY_KEY_LABEL,
                            value="Temperature",
                            language="en",
                        ),
                        create_property(
                            key=PROPERTY_KEY_COMMENT,
                            value="Random Temperature",
                            language="en",
                        ),
                    ],
                    values=[
                        create_value(
                            label="reading",
                            comment="Temperature in degrees Celsius",
                            unit=UNIT_DEGREE_CELSIUS,
                            data_type="integer",
                        )
                    ],
                )
            ],
            location=create_location(lat=51.5, lon=-0.1),
        )

        twin_from_model_did_list.append(twin_from_model_did)

    try:
        while True:
            # Share random temperature using the Twins from Model
            publisher.share_random_data(twin_from_model_did_list)
            sleep(3)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
