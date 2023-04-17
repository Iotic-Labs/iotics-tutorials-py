import logging
import random
import sys
import threading
from time import sleep
from typing import List
from collections import namedtuple
from helpers.constants import (
    PROPERTY_KEY_COLOR,
    PROPERTY_KEY_COMMENT,
    PROPERTY_KEY_CREATED_BY,
    PROPERTY_KEY_FROM_MODEL,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_SPACE_NAME,
    PROPERTY_KEY_TYPE,
    PROPERTY_VALUE_MODEL,
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


class HelicoptersConnector:
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

    def share_random_data(self, twin_from_model_did_list: List[str]):
        for twin_from_model_did in twin_from_model_did_list:
            aircraft_hours = {"hours": random.randint(1, 100)}

            self._iotics_api.share_feed_data(
                twin_did=twin_from_model_did,
                feed_id="aircraft_hours",
                data=aircraft_hours,
            )

            logging.info("Shared %s from Twin %s", aircraft_hours, twin_from_model_did)

            missiles_fired = {"n_missiles": random.randint(1, 50)}

            self._iotics_api.share_feed_data(
                twin_did=twin_from_model_did,
                feed_id="missiles_fired",
                data=missiles_fired,
            )

            logging.info("Shared %s from Twin %s", missiles_fired, twin_from_model_did)

    def change_location(self, twin_from_model_did_list: List[str]):
        for twin_from_model_did in twin_from_model_did_list:
            new_location = LOCATION_LIST[random.randint(0, len(LOCATION_LIST - 1))]

            self._iotics_api.update_twin(
                twin_did=twin_from_model_did,
                location=create_location(lat=new_location.lat, lon=new_location.lon),
            )

            logging.info(
                "New Location of Twin %s: LAT=%f, LON=%f",
                twin_from_model_did,
                new_location.lat,
                twin_from_model_did,
            )

            # We need the HQ Twin info
            self._iotics_api.send_input_message(
                sender_twin_id=twin_from_model_did,
                receiver_twin_id="hq_twin",
                input_id="new_location",
                message={"new_lat": new_location.lat, "new_lon": new_location.lon},
            )

            logging.info("Sent new location to HQ Twin")

    def search_for_hq_twin(self):
        logging.info("Searching for HQ Twin...")
        twins_found_list = []
        payload = self._iotics_api.get_search_payload(
            properties=[
                create_property(key=PROPERTY_KEY_LABEL, value="HQ Twin", language="en")
            ],
            response_type="FULL",
        )

        while not twins_found_list:
            for response in self._iotics_api.search_iter(
                client_app_id="hq_connector", payload=payload
            ):
                twins = response.payload.twins
                twins_found_list.extend(twins)

            logging.info("Found %s HQ Twins", len(twins_found_list))
            if not twins_found_list:
                sleep(5)

        hq_twin = twins_found_list[0]

        return hq_twin


def main():
    connector = HelicoptersConnector()

    # Create Twin Model
    twin_model_did = connector.create_new_twin(
        twin_key_name="HelicopterModel",
        properties=[
            create_property(
                key=PROPERTY_KEY_TYPE, value=PROPERTY_VALUE_MODEL, is_uri=True
            ),
            create_property(
                key=PROPERTY_KEY_LABEL, value="Helicopter Model", language="en"
            ),
            create_property(
                key=PROPERTY_KEY_COMMENT,
                value="Model of a Helicopter Twin",
                language="en",
            ),
            create_property(key=PROPERTY_KEY_SPACE_NAME, value="demo"),
            create_property(key=PROPERTY_KEY_COLOR, value="#9aceff"),
            create_property(key=PROPERTY_KEY_CREATED_BY, value="Lorenzo"),
        ],
        feeds=[
            create_feed_with_meta(
                feed_id="aircraft_hours",
                properties=[
                    create_property(
                        key=PROPERTY_KEY_LABEL, value="Aircraft Hours", language="en"
                    ),
                ],
                values=[create_value(label="hours", data_type="integer")],
            ),
            create_feed_with_meta(
                feed_id="missiles_fired",
                properties=[
                    create_property(
                        key=PROPERTY_KEY_LABEL, value="Missiles Fired", language="en"
                    ),
                ],
                values=[create_value(label="missiles", data_type="integer")],
            ),
        ],
    )

    # Create 3 Twins from Model
    twin_from_model_did_list = []
    for helicopter in range(3):
        twin_from_model_did = connector.create_new_twin(
            twin_key_name=f"Helicopter{helicopter}",
            properties=[
                create_property(
                    key=PROPERTY_KEY_FROM_MODEL, value=twin_model_did, is_uri=True
                ),
                create_property(
                    key=PROPERTY_KEY_LABEL,
                    value=f"Helicopter {helicopter+1}",
                    language="en",
                ),
                create_property(key=PROPERTY_KEY_SPACE_NAME, value="demo"),
                create_property(key=PROPERTY_KEY_COLOR, value="#9aceff"),
                create_property(key=PROPERTY_KEY_CREATED_BY, value="Lorenzo"),
            ],
            feeds=[
                create_feed_with_meta(
                    feed_id="aircraft_hours",
                    properties=[
                        create_property(
                            key=PROPERTY_KEY_LABEL,
                            value="Aircraft Hours",
                            language="en",
                        ),
                    ],
                    values=[create_value(label="hours", data_type="integer")],
                ),
                create_feed_with_meta(
                    feed_id="missiles_fired",
                    properties=[
                        create_property(
                            key=PROPERTY_KEY_LABEL,
                            value="Missiles Fired",
                            language="en",
                        ),
                    ],
                    values=[create_value(label="n_missiles", data_type="integer")],
                ),
            ],
            location=create_location(
                lat=LOCATION_LIST[0].lat, lon=LOCATION_LIST[0].lon
            ),  # London
        )

        twin_from_model_did_list.append(twin_from_model_did)

    helicop

    try:
        while True:
            # Share random data using the Twins from Model
            connector.share_random_data(twin_from_model_did_list)
            connector.change_location(twin_from_model_did_list)
            sleep(3)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
