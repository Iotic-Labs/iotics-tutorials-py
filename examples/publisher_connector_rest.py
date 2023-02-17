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
from helpers.rest_client import RestClient
from helpers.utilities import auto_refresh_token_rest_stomp, get_host_endpoints

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


class PublisherConnectorRest:
    def __init__(self):
        self._identity: Identity = None
        self._host_id: str = None
        self._rest_client: RestClient = None

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
        token = self._identity.get_token()
        self._rest_client = RestClient(token=token, host_url=HOST_URL)

        threading.Thread(
            target=auto_refresh_token_rest_stomp,
            args=(
                self._identity,
                self._rest_client,
            ),
            daemon=True,
        ).start()

        self._host_id = self._rest_client.get_host_id()

    @property
    def local_host_id(self) -> str:
        return self._host_id

    def create_new_twin(
        self,
        twin_key_name: str,
        properties: List[dict],
        feeds: List[dict] = None,
        location: dict = None,
    ) -> str:
        twin_identity = self._identity.create_twin_with_control_delegation(
            twin_key_name=twin_key_name
        )

        twin_did = twin_identity.did

        self._rest_client.upsert_twin(
            twin_did=twin_did,
            host_id=self._host_id,
            properties=properties,
            feeds=feeds,
            location=location,
        )

        return twin_did

    def share_random_data(self, twin_from_model_did_list: List[str]):
        for twin_from_model_did in twin_from_model_did_list:
            self._rest_client.share_data(
                publisher_twin_did=twin_from_model_did,
                host_id=self._host_id,
                feed_id="temperature",
                data_to_share={"reading": random.randint(10, 31)},
            )


def main():
    publisher = PublisherConnectorRest()

    # Create Twin Model
    twin_model_did = publisher.create_new_twin(
        twin_key_name="SensorTwinModel",
        properties=[
            {
                "key": PROPERTY_KEY_TYPE,
                "uriValue": {"value": PROPERTY_VALUE_MODEL},
            },
            {
                "key": PROPERTY_KEY_LABEL,
                "langLiteralValue": {
                    "value": "Temperature Sensor Model",
                    "lang": "en",
                },
            },
            {
                "key": PROPERTY_KEY_COMMENT,
                "langLiteralValue": {
                    "value": "Model of a Temperature Sensor Twin",
                    "lang": "en",
                },
            },
            {
                "key": PROPERTY_KEY_SPACE_NAME,
                "stringLiteralValue": {"value": "Replace with Space Name"},
            },
            {
                "key": PROPERTY_KEY_COLOR,
                "stringLiteralValue": {"value": "#9aceff"},
            },
            {
                "key": PROPERTY_KEY_CREATED_BY,
                "stringLiteralValue": {"value": "Replace with your Name"},
            },
            {
                "key": "https://data.iotics.com/app#defines",
                "uriValue": {"value": "https://saref.etsi.org/core/TemperatureSensor"},
            },
            {
                "key": "https://saref.etsi.org/core/hasModel",
                "stringLiteralValue": {"value": "SET-LATER"},
            },
        ],
        feeds=[
            {
                "id": "temperature",
                "storeLast": True,
                "properties": [
                    {
                        "key": PROPERTY_KEY_LABEL,
                        "langLiteralValue": {
                            "value": "Temperature",
                            "lang": "en",
                        },
                    },
                    {
                        "key": PROPERTY_KEY_COMMENT,
                        "langLiteralValue": {
                            "value": "Random Temperature",
                            "lang": "en",
                        },
                    },
                ],
                "values": [
                    {
                        "comment": "Temperature in degrees Celsius",
                        "dataType": "integer",
                        "label": "reading",
                        "unit": UNIT_DEGREE_CELSIUS,
                    }
                ],
            },
        ],
    )

    # Create 3 Twins from Model
    twin_from_model_did_list = []
    for temp_sensor in range(3):
        twin_from_model_did = publisher.create_new_twin(
            twin_key_name=f"SensorTwin{temp_sensor}",
            properties=[
                {
                    "key": PROPERTY_KEY_FROM_MODEL,
                    "uriValue": {"value": twin_model_did},
                },
                {
                    "key": PROPERTY_KEY_LABEL,
                    "langLiteralValue": {
                        "value": f"Temperature Sensor Twin {temp_sensor+1}",
                        "lang": "en",
                    },
                },
                {
                    "key": PROPERTY_KEY_COMMENT,
                    "langLiteralValue": {
                        "value": f"Temperature Sensor Twin {temp_sensor+1} that shares random temperature data",
                        "lang": "en",
                    },
                },
                {
                    "key": PROPERTY_KEY_SPACE_NAME,
                    "stringLiteralValue": {"value": "Replace with Space Name"},
                },
                {
                    "key": PROPERTY_KEY_COLOR,
                    "stringLiteralValue": {"value": "#9aceff"},
                },
                {
                    "key": PROPERTY_KEY_CREATED_BY,
                    "stringLiteralValue": {"value": "Replace with your Name"},
                },
                {
                    "key": "https://data.iotics.com/app#defines",
                    "uriValue": {
                        "value": "https://saref.etsi.org/core/TemperatureSensor"
                    },
                },
                {
                    "key": "https://saref.etsi.org/core/hasModel",
                    "stringLiteralValue": {"value": "T1234"},
                },
                {
                    "key": PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
                    "uriValue": {"value": PROPERTY_VALUE_ALLOW_ALL},
                },
                {
                    "key": PROPERTY_KEY_HOST_ALLOW_LIST,
                    "uriValue": {"value": PROPERTY_VALUE_ALLOW_ALL},
                },
            ],
            feeds=[
                {
                    "id": "temperature",
                    "storeLast": True,
                    "properties": [
                        {
                            "key": PROPERTY_KEY_LABEL,
                            "langLiteralValue": {
                                "value": "Temperature",
                                "lang": "en",
                            },
                        },
                        {
                            "key": PROPERTY_KEY_COMMENT,
                            "langLiteralValue": {
                                "value": "Random Temperature",
                                "lang": "en",
                            },
                        },
                    ],
                    "values": [
                        {
                            "comment": "Temperature in degrees Celsius",
                            "dataType": "integer",
                            "label": "reading",
                            "unit": UNIT_DEGREE_CELSIUS,
                        }
                    ],
                },
            ],
            location={"lat": 51.5, "lon": -0.1},
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
