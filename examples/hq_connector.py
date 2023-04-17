import json
import logging
import random
import sys
import threading
from collections import namedtuple
from time import sleep
from typing import List

from helpers.constants import (
    PROPERTY_KEY_COLOR,
    PROPERTY_KEY_CREATED_BY,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_SPACE_NAME,
)
from helpers.identity import Identity
from helpers.utilities import auto_refresh_token_grpc, get_host_endpoints
from iotics.api.common_pb2 import GeoLocation, Property
from iotics.lib.grpc.helpers import (
    create_input_with_meta,
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

Location = namedtuple("Location", ["lat", "lon"])

LOCATION_LIST = [
    Location(lat=51.5, lon=-0.1),  # London
    Location(lat=48.84, lon=2.31),  # Paris
    Location(lat=50.84, lon=4.35),  # Brussels
    Location(lat=52.36, lon=4.88),  # Amsterdam
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class HQConnector:
    def __init__(self):
        self._identity: Identity = None
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

    def wait_for_new_locations(self, hq_twin_did: str):
        input_listener = self._iotics_api.receive_input_messages(
            twin_id=hq_twin_did, input_id="new_location"
        )

        print("Waiting for Input messages...")
        for message in input_listener:
            data = json.loads(message.payload.message.data)
            logging.info("Received new location: %s", data)


def main():
    connector = HQConnector()

    # Create HQ Twin
    hq_twin_did = connector.create_new_twin(
        twin_key_name="HQ_Twin",
        properties=[
            create_property(key=PROPERTY_KEY_LABEL, value="HQ Twin", language="en"),
            create_property(key=PROPERTY_KEY_SPACE_NAME, value="demo"),
            create_property(key=PROPERTY_KEY_COLOR, value="#9aceff"),
            create_property(key=PROPERTY_KEY_CREATED_BY, value="Lorenzo"),
        ],
        inputs=[
            create_input_with_meta(
                input_id="new_location",
                properties=[
                    create_property(
                        key=PROPERTY_KEY_LABEL, value="New Location", language="en"
                    ),
                ],
                values=[
                    create_value(label="new_lat", data_type="float"),
                    create_value(label="new_lon", data_type="float"),
                ],
            ),
        ],
        location=create_location(
            lat=LOCATION_LIST[0].lat, lon=LOCATION_LIST[0].lon
        ),  # London
    )

    try:
        while True:
            # Wait for Helicopters' new locations
            connector.wait_for_new_locations(hq_twin_did=hq_twin_did)
            sleep(3)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
