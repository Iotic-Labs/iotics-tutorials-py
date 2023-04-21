import json
import logging
import sys
from threading import Thread
from typing import List

import grpc
from helpers.constants import (
    AGENT_KEY_NAME,
    AGENT_SEED,
    HOST_URL,
    LOCATION_LIST,
    PROPERTY_KEY_COLOR,
    PROPERTY_KEY_CREATED_BY,
    PROPERTY_KEY_HOST_ALLOW_LIST,
    PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_SPACE_NAME,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.identity import Identity
from helpers.utilities import auto_refresh_token_grpc, get_host_endpoints
from iotics.api.common_pb2 import GeoLocation, Property
from iotics.lib.grpc.helpers import (
    create_feed_with_meta,
    create_input_with_meta,
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


def forward_data(iotics_api: IOTICSviagRPC, data_received, shadow_twin_did, feed_id):
    logging.debug("Forwarding data %s from Twin %s", data_received, shadow_twin_did)
    iotics_api.share_feed_data(
        twin_did=shadow_twin_did,
        feed_id=feed_id,
        data=data_received,
    )


def get_feed_data(iotics_api: IOTICSviagRPC, feed_listener, shadow_twin_did, feed_id):
    for latest_feed_data in feed_listener:
        data_received = json.loads(latest_feed_data.payload.feedData.data)

        forward_data(iotics_api, data_received, shadow_twin_did, feed_id)


def follow_original(
    iotics_api: IOTICSviagRPC,
    shadow_twin_did: str,
    original_twin_did: str,
    original_feed_id: str,
):
    feed_listener = iotics_api.fetch_interests(
        follower_twin_did=shadow_twin_did,
        followed_twin_did=original_twin_did,
        followed_feed_id=original_feed_id,
    )

    try:
        get_feed_data(
            iotics_api=iotics_api,
            feed_listener=feed_listener,
            shadow_twin_did=shadow_twin_did,
            feed_id=original_feed_id,
        )
    except grpc._channel._MultiThreadedRendezvous:
        follow_original(
            iotics_api=iotics_api,
            shadow_twin_did=shadow_twin_did,
            original_twin_did=original_twin_did,
            original_feed_id=original_feed_id,
        )
    except grpc._channel._InactiveRpcError:
        pass


class HQConnector:
    def __init__(self):
        self._identity: Identity = None
        self._iotics_api: IOTICSviagRPC = None
        self._shadow_twins: dict = None
        self._threads_list: List[Thread] = []

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
            token_duration=3000,
        )
        self._iotics_api = IOTICSviagRPC(auth=self._identity)
        self._shadow_twins = {}

        Thread(
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

        self._iotics_api.upsert_twin(
            twin_did=twin_did,
            location=location,
            properties=properties,
            feeds=feeds,
            inputs=inputs,
        )

        return twin_did

    def _replace_label(self, twin_properties):
        new_twin_property_list = []
        for twin_property in twin_properties:
            if twin_property.key == PROPERTY_KEY_LABEL:
                new_label = twin_property.langLiteralValue.value + " Shadow"
                new_property = create_property(
                    key=PROPERTY_KEY_LABEL,
                    language=twin_property.langLiteralValue.lang,
                    value=new_label,
                )
                new_twin_property_list.append(new_property)
                continue

            new_twin_property_list.append(twin_property)

        return new_twin_property_list, new_label

    def _change_sharing_permissions(self, twin_properties, twin_location):
        new_twin_property_list = []

        if twin_location.lat == LOCATION_LIST[1].lat:
            host_id = LOCATION_LIST[1].host_id
        elif twin_location.lat == LOCATION_LIST[2].lat:
            host_id = LOCATION_LIST[2].host_id

        for twin_property in twin_properties:
            # Data Allow List
            if twin_property.key == PROPERTY_KEY_HOST_ALLOW_LIST:
                new_property = create_property(
                    key=PROPERTY_KEY_HOST_ALLOW_LIST,
                    value=host_id,
                    is_uri=True,
                )

                new_twin_property_list.append(new_property)
                continue

            # Metadata Allow List
            if twin_property.key == PROPERTY_KEY_HOST_METADATA_ALLOW_LIST:
                new_property = create_property(
                    key=PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
                    value=host_id,
                    is_uri=True,
                )

                new_twin_property_list.append(new_property)
                continue

            new_twin_property_list.append(twin_property)

        return new_twin_property_list

    def _create_shadow(
        self,
        twin_description,
        original_twin_did,
        twin_location,
    ):
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
                    feed_id=feed_id,
                    properties=feed_properties,
                    values=feed_values,
                )
            )

        original_twin_properties = twin_description.payload.result.properties
        shadow_twin_properties, new_label = self._replace_label(
            twin_properties=original_twin_properties
        )
        selective_sharing_properties = self._change_sharing_permissions(
            twin_properties=shadow_twin_properties, twin_location=twin_location
        )

        shadow_twin_did = self.create_new_twin(
            twin_key_name=f"shadow_{original_twin_did[-5:]}",
            properties=selective_sharing_properties,
            feeds=feeds_list,
            location=twin_location,
        )

        logging.info("Created Twin %s", new_label)

        self._shadow_twins.update(
            {
                original_twin_did: {
                    "shadow_twin_did": shadow_twin_did,
                    "lat": str(twin_location.lat),
                    "label": new_label,
                }
            }
        )

        for feed in twin_feeds:
            Thread(
                target=follow_original,
                args=(
                    self._iotics_api,
                    shadow_twin_did,
                    original_twin_did,
                    feed.feedId.id,
                ),
                daemon=True,
            ).start()

    def _delete_shadow(self, original_twin_did):
        shadow_twin = self._shadow_twins.get(original_twin_did)

        if shadow_twin:
            shadow_twin_did = shadow_twin["shadow_twin_did"]
            shadow_twin_label = shadow_twin["label"]
            logging.info(
                "Helicopter back to %s. Deleting %s",
                LOCATION_LIST[0].location_name,
                shadow_twin_label,
            )
            self._iotics_api.delete_twin(twin_did=shadow_twin_did)
            self._shadow_twins.pop(original_twin_did)

    def _update_shadow(self, original_twin_did: str, twin_location):
        shadow_twin = self._shadow_twins.get(original_twin_did)
        shadow_label = shadow_twin["label"]
        shadow_twin_did = shadow_twin["shadow_twin_did"]

        if twin_location.lat == LOCATION_LIST[1].lat:
            new_lat = LOCATION_LIST[1].lat
            new_lon = LOCATION_LIST[1].lon
            host_id = LOCATION_LIST[1].host_id
            self._shadow_twins[original_twin_did]["lat"] = new_lat
        elif twin_location.lat == LOCATION_LIST[2].lat:
            new_lat = LOCATION_LIST[2].lat
            new_lon = LOCATION_LIST[2].lon
            host_id = LOCATION_LIST[2].host_id
            self._shadow_twins[original_twin_did]["lat"] = new_lat

        self._iotics_api.update_twin(
            twin_did=shadow_twin_did,
            location=create_location(lat=new_lat, lon=new_lon),
            props_keys_deleted=[
                PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
                PROPERTY_KEY_HOST_ALLOW_LIST,
            ],
            props_added=[
                create_property(
                    key=PROPERTY_KEY_HOST_ALLOW_LIST, value=host_id, is_uri=True
                ),
                create_property(
                    key=PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
                    value=host_id,
                    is_uri=True,
                ),
            ],
        )

        logging.info("Updated Shadow Twin %s", shadow_label)

    def _take_action(self, original_twin_did: str):
        twin_description = self._iotics_api.describe_twin(twin_did=original_twin_did)

        twin_location = twin_description.payload.result.location

        # Create/Update Shadow
        if str(twin_location.lat) != str(LOCATION_LIST[0].lat):
            shadow_twin = self._shadow_twins.get(original_twin_did)
            # Create new Shadow
            if not shadow_twin:
                self._create_shadow(
                    twin_description=twin_description,
                    original_twin_did=original_twin_did,
                    twin_location=twin_location,
                )
            # Update existing Shadow
            elif shadow_twin["lat"] != str(twin_location.lat):
                self._update_shadow(
                    original_twin_did=original_twin_did, twin_location=twin_location
                )
        # Twin back to Base
        else:
            self._delete_shadow(original_twin_did=original_twin_did)

    def wait_for_new_locations(self, hq_twin_did: str):
        input_listener = self._iotics_api.receive_input_messages(
            twin_id=hq_twin_did, input_id="new_location"
        )

        for message in input_listener:
            data = json.loads(message.payload.message.data)
            new_location = data["new_location"]
            twin_did = data["twin_did"]
            twin_label = data["twin_label"]

            logging.info("Received location of Twin %s: %s", twin_label, new_location)
            self._take_action(original_twin_did=twin_did)

    def clear_space(self):
        twins_found_list = []
        text_to_search = "helicopter"
        payload = self._iotics_api.get_search_payload(text=text_to_search)

        for response in self._iotics_api.search_iter(
            client_app_id="hq_connector", payload=payload
        ):
            twins = response.payload.twins
            twins_found_list.extend(twins)

            logging.debug("Found %d %s Twins", len(twins_found_list), text_to_search)

        for twin in twins_found_list:
            twin_id = twin.twinId.id
            self._iotics_api.delete_twin(twin_did=twin_id)


def main():
    connector = HQConnector()

    # connector.clear_space()

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
                    create_value(label="new_location", data_type="string"),
                    create_value(label="twin_did", data_type="string"),
                    create_value(label="twin_label", data_type="string"),
                ],
            ),
        ],
        location=create_location(lat=LOCATION_LIST[0].lat, lon=LOCATION_LIST[0].lon),
    )

    logging.info("HQ Twin created")

    try:
        # Wait for Helicopters' new locations
        connector.wait_for_new_locations(hq_twin_did=hq_twin_did)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
