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
    PROPERTY_KEY_HOST_ALLOW_LIST,
    PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_SPACE_NAME,
    PROPERTY_VALUE_ALLOW_ALL,
)
from helpers.identity import Identity
from helpers.utilities import auto_refresh_token_grpc, get_host_endpoints
from iotics.api.common_pb2 import GeoLocation, Property
from iotics.lib.grpc.helpers import (
    create_input_with_meta,
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


def follow_original(
    iotics_api: IOTICSviagRPC,
    shadow_twin_did: str,
    original_twin_did: str,
    original_feed_id: str,
    event: threading.Event,
):
    feed_listener = iotics_api.fetch_interests(
        follower_twin_did=shadow_twin_did,
        followed_twin_did=original_twin_did,
        followed_feed_id=original_feed_id,
    )

    for latest_feed_data in feed_listener:
        if event.is_set():
            break

        data_received = json.loads(latest_feed_data.payload.feedData.data)

        print(f"Forwarding data {data_received} from Twin {shadow_twin_did}")
        iotics_api.share_feed_data(
            twin_did=shadow_twin_did,
            feed_id=original_feed_id,
            data=data_received,
        )


class HQConnector:
    def __init__(self):
        self._identity: Identity = None
        self._iotics_api: IOTICSviagRPC = None
        self._shadow_twins: dict = None
        self._threads_list: List[threading.Thread] = []

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
            token_duration=300,
        )
        self._iotics_api = IOTICSviagRPC(auth=self._identity)
        self._shadow_twins = {}

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
        inputs: List[dict] = None,
        location: GeoLocation = None,
    ) -> str:
        twin_identity = self._identity.create_twin_with_control_delegation(
            twin_key_name=twin_key_name
        )

        twin_did = twin_identity.did

        resp = self._iotics_api.upsert_twin(
            twin_did=twin_did,
            location=location,
            properties=properties,
            feeds=feeds,
            inputs=inputs,
        )
        if resp:
            logging.info("Twin %s upserted", twin_did)

        return twin_did

    def _replace_label(self, twin_properties):
        new_twin_property_list = []
        for twin_property in twin_properties:
            if twin_property.key == PROPERTY_KEY_LABEL:
                new_property = create_property(
                    key=PROPERTY_KEY_LABEL,
                    language=twin_property.langLiteralValue.lang,
                    value=twin_property.langLiteralValue.value + " Shadow",
                )
                new_twin_property_list.append(new_property)
                continue

            new_twin_property_list.append(twin_property)

        return new_twin_property_list

    def _change_sharing_permissions(self, twin_properties):
        new_twin_property_list = []
        for twin_property in twin_properties:
            # Data Allow List
            if twin_property.key == PROPERTY_KEY_HOST_ALLOW_LIST:
                new_property = create_property(
                    key=PROPERTY_KEY_HOST_ALLOW_LIST,
                    value=PROPERTY_VALUE_ALLOW_ALL,
                    is_uri=True,
                )

                new_twin_property_list.append(new_property)
                continue

            # Metadata Allow List
            if twin_property.key == PROPERTY_KEY_HOST_METADATA_ALLOW_LIST:
                new_property = create_property(
                    key=PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
                    value=PROPERTY_VALUE_ALLOW_ALL,
                    is_uri=True,
                )

                new_twin_property_list.append(new_property)
                continue

            new_twin_property_list.append(twin_property)

        return new_twin_property_list

    def _update_shadow(self, original_twin_did: str):
        twin_description = self._iotics_api.describe_twin(twin_did=original_twin_did)

        original_twin_properties = twin_description.payload.result.properties
        twin_location = twin_description.payload.result.location

        if str(twin_location.lat) != str(
            LOCATION_LIST[0].lat
        ) and not self._shadow_twins.get(original_twin_did):
            feeds_list = []
            twin_feeds = twin_description.payload.result.feeds
            for feed in twin_feeds:
                feed_id = feed.feedId.id

                feed_description = self._iotics_api.describe_feed(
                    twin_did=original_twin_did, feed_id=feed_id
                )
                feed_properties = feed_description.payload.result.properties

                feed_values = feed_description.payload.result.values

                feeds_list.append(
                    create_feed_with_meta(
                        feed_id=feed_id, properties=feed_properties, values=feed_values
                    )
                )

            shadow_twin_properties = self._replace_label(
                twin_properties=original_twin_properties
            )
            selective_sharing_properties = self._change_sharing_permissions(
                twin_properties=shadow_twin_properties
            )

            shadow_twin_did = self.create_new_twin(
                twin_key_name=f"shadow_{original_twin_did[-5:]}",
                properties=selective_sharing_properties,
                feeds=feeds_list,
                location=twin_location,
            )

            logging.info("Created shadow Twin")

            event = threading.Event()
            event.clear()

            self._shadow_twins.update(
                {
                    original_twin_did: {
                        "shadow_twin_did": shadow_twin_did,
                        "event": event,
                    }
                }
            )

            for feed in twin_feeds:
                threading.Thread(
                    target=follow_original,
                    args=(
                        self._iotics_api,
                        shadow_twin_did,
                        original_twin_did,
                        feed.feedId.id,
                        event,
                    ),
                    daemon=True,
                ).start()

        else:
            shadow_twin_did = None
            try:
                shadow_twin_did = self._shadow_twins[original_twin_did][
                    "shadow_twin_did"
                ]
            except KeyError:
                logging.info("Helicopter already in London")
            else:
                event: threading.Event = self._shadow_twins[original_twin_did]["event"]
                event.set()
                self._iotics_api.delete_twin(twin_did=shadow_twin_did)

                logging.info("Helicopter back in London. Deleting Shadow Twin")

    def wait_for_new_locations(self, hq_twin_did: str):
        input_listener = self._iotics_api.receive_input_messages(
            twin_id=hq_twin_did, input_id="new_location"
        )

        print("Waiting for Input messages...")
        for message in input_listener:
            data = json.loads(message.payload.message.data)
            new_lat = data["new_lat"]
            new_lon = data["new_lon"]
            twin_did = data["twin_did"]

            logging.info(
                "Received new lat=%s, lon=%s from Twin %s", new_lat, new_lon, twin_did
            )
            self._update_shadow(original_twin_did=twin_did)


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
                    create_value(label="twin_did", data_type="string"),
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
