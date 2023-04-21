import logging
import random
import sys
import threading
from time import sleep
from typing import List

from helpers.constants import (
    AGENT_KEY_NAME,
    AGENT_SEED,
    HOST_URL,
    LOCATION_LIST,
    PROPERTY_KEY_COLOR,
    PROPERTY_KEY_CREATED_BY,
    PROPERTY_KEY_FROM_MODEL,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_SPACE_NAME,
    PROPERTY_KEY_TYPE,
    PROPERTY_VALUE_MODEL,
    USER_KEY_NAME,
    USER_SEED,
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


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
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

        self._iotics_api.upsert_twin(
            twin_did=twin_did, location=location, properties=properties, feeds=feeds
        )

        return twin_did

    def share_random_data(self, twin_from_model_did_dict: dict):
        for twin_from_model_did, twin_label in twin_from_model_did_dict.items():
            aircraft_hours = {"hours": random.randint(1, 100)}

            self._iotics_api.share_feed_data(
                twin_did=twin_from_model_did,
                feed_id="aircraft_hours",
                data=aircraft_hours,
            )

            logging.debug("Shared %s from Twin %s", aircraft_hours, twin_label)

            missiles_fired = {"n_missiles": random.randint(1, 50)}

            self._iotics_api.share_feed_data(
                twin_did=twin_from_model_did,
                feed_id="missiles_fired",
                data=missiles_fired,
            )

            logging.debug("Shared %s from Twin %s", missiles_fired, twin_label)

    def change_location(self, twin_from_model_did_dict: dict, hq_twin):
        hq_twin_did = hq_twin.twinId.id
        hq_twin_input_id = hq_twin.inputs[0].inputId.id

        for twin_from_model_did, twin_label in twin_from_model_did_dict.items():
            new_location = LOCATION_LIST[random.randint(0, len(LOCATION_LIST) - 1)]

            self._iotics_api.update_twin(
                twin_did=twin_from_model_did,
                location=create_location(lat=new_location.lat, lon=new_location.lon),
            )

            logging.info(
                "New Location of Twin %s: %s", twin_label, new_location.location_name
            )

            # We need the HQ Twin info
            self._iotics_api.send_input_message(
                sender_twin_id=twin_from_model_did,
                receiver_twin_id=hq_twin_did,
                input_id=hq_twin_input_id,
                message={
                    "new_location": new_location.location_name,
                    "twin_did": twin_from_model_did,
                    "twin_label": twin_label,
                },
            )

            logging.debug("Sent new location to HQ Twin")

    def search_for_hq_twin(self):
        logging.debug("Searching for HQ Twin...")
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

            logging.debug("Found %s HQ Twins", len(twins_found_list))
            if not twins_found_list:
                sleep(3)

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
    twin_from_model_did_dict = {}
    for helicopter in range(3):
        twin_label = f"Helicopter {helicopter+1}"
        twin_from_model_did = connector.create_new_twin(
            twin_key_name=f"Helicopter{helicopter}",
            properties=[
                create_property(
                    key=PROPERTY_KEY_FROM_MODEL, value=twin_model_did, is_uri=True
                ),
                create_property(
                    key=PROPERTY_KEY_LABEL, value=twin_label, language="en"
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
            ),
        )

        twin_from_model_did_dict.update({twin_from_model_did: twin_label})

        logging.info("Created Twin %s", twin_label)

    hq_twin = connector.search_for_hq_twin()
    logging.info("---")
    # input()

    try:
        while True:
            # Share random data using the Twins from Model
            connector.share_random_data(twin_from_model_did_dict)
            connector.change_location(
                twin_from_model_did_dict=twin_from_model_did_dict, hq_twin=hq_twin
            )
            # input()
            logging.info("---")
            sleep(3)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
