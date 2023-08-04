"""
"""

import json
import threading
from time import sleep
from typing import List

import grpc

from helpers.constants import (
    ALLOW_ALL,
    CREATED_BY,
    ELECTRIC_ENGINE,
    FUEL_TYPE,
    HOST_ALLOW_LIST,
    HOST_METADATA_ALLOW_LIST,
    INDEX_URL,
    LABEL,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.identity_interface import IdentityInterface
from helpers.utilities import make_api_call
from iotics.lib.grpc.helpers import (
    create_feed_with_meta,
    create_property,
)
from iotics.lib.grpc.iotics_api import IoticsApi
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)

HOST_URL: str = ""

AGENT_KEY_NAME: str = ""
AGENT_SEED: str = ""

FEED_IDS_TO_HIDE = ["speed"]
PROPERTY_KEYS_TO_HIDE = [CREATED_BY]


def main():
    iotics_index: dict = make_api_call(
        method="GET", endpoint=INDEX_URL.format(host_url=HOST_URL)
    )
    resolver_url: str = iotics_index.get("resolver")
    grpc_url: str = iotics_index.get("grpc")

    identity_api: HighLevelIdentityApi = get_rest_high_level_identity_api(
        resolver_url=resolver_url
    )

    identity_interface: IdentityInterface = IdentityInterface(
        grpc_endpoint=grpc_url, identity_api=identity_api
    )

    (
        user_identity,
        agent_identity,
    ) = identity_api.create_user_and_agent_with_auth_delegation(
        user_seed=bytes.fromhex(USER_SEED),
        user_key_name=USER_KEY_NAME,
        agent_seed=bytes.fromhex(AGENT_SEED),
        agent_key_name=AGENT_KEY_NAME,
    )

    identity_interface.refresh_token(
        user_identity=user_identity, agent_identity=agent_identity, token_duration=60
    )

    iotics_api = IoticsApi(auth=identity_interface)

    search_criteria = iotics_api.get_search_payload(
        properties=[
            create_property(key=FUEL_TYPE, value=ELECTRIC_ENGINE, is_uri=True),
            create_property(key=CREATED_BY, value="Michael Joseph Jackson"),
        ],
        response_type="FULL",
    )

    twins_found_list = []
    for response in iotics_api.search_iter(
        client_app_id="search_twins", payload=search_criteria
    ):
        twins = response.payload.twins
        twins_found_list.extend(twins)

    print(f"Found {len(twins_found_list)} Twin(s) based on the search criteria")
    print("---")

    def receive_and_forward_feed_data(
        feed_listener, wait_for_twin_creation: threading.Event
    ):
        wait_for_twin_creation.wait()

        try:
            for latest_feed_data in feed_listener:
                try:
                    feed_data_payload = latest_feed_data.payload
                    followed_twin_id = feed_data_payload.interest.followedFeedId.twinId
                    follower_twin_id = feed_data_payload.interest.followerTwinId.id
                    followed_feed_id = feed_data_payload.interest.followedFeedId.id
                    received_data = json.loads(feed_data_payload.feedData.data)
                    occurred_at = feed_data_payload.feedData.occurredAt
                except AttributeError as ex:
                    print("An exception was raised when receiving Feed Data", ex)
                else:
                    iotics_api.share_feed_data(
                        twin_did=follower_twin_id,
                        feed_id=followed_feed_id,
                        data=received_data,
                        occurred_at=occurred_at.seconds,
                    )
                    print(
                        f"Forwarded data sample received from Twin {followed_twin_id}"
                    )

        except grpc._channel._MultiThreadedRendezvous:
            print("Token expired")

    for count, car_twin in enumerate(twins_found_list):
        twin_shadow_identity: RegisteredIdentity = (
            identity_api.create_twin_with_control_delegation(
                twin_key_name=f"TwinCarShadow{count}",
                twin_seed=bytes.fromhex(AGENT_SEED),
                agent_registered_identity=agent_identity,
            )
        )

        car_twin_id: str = car_twin.twinId.id
        car_twin_properties: List[dict] = car_twin.properties
        twin_shadow_properties: List[dict] = [
            create_property(key=HOST_ALLOW_LIST, value=ALLOW_ALL, is_uri=True),
            create_property(key=HOST_METADATA_ALLOW_LIST, value=ALLOW_ALL, is_uri=True),
        ]

        for car_twin_property in car_twin_properties:
            if car_twin_property.key in PROPERTY_KEYS_TO_HIDE:
                continue

            if car_twin_property.key == LABEL:
                car_twin_property.langLiteralValue.value += " Shadow"

            twin_shadow_properties.append(car_twin_property)

        car_twin_feeds: List[dict] = car_twin.feeds
        shadow_twin_feeds: List[dict] = []
        wait_for_twin_creation: threading.Event = threading.Event()
        for car_twin_feed in car_twin_feeds:
            feed_id: str = car_twin_feed.feedId.id
            if feed_id in FEED_IDS_TO_HIDE:
                continue

            feed_description = iotics_api.describe_feed(
                twin_did=car_twin_id, feed_id=feed_id
            )

            shadow_twin_feeds.append(
                create_feed_with_meta(
                    feed_id=feed_id,
                    store_last=feed_description.payload.result.storeLast,
                    properties=feed_description.payload.result.properties,
                    values=feed_description.payload.result.values,
                )
            )

            feed_listener = iotics_api.fetch_interests(
                follower_twin_did=twin_shadow_identity.did,
                followed_twin_did=car_twin_id,
                followed_feed_id=feed_id,
            )

            threading.Thread(
                target=receive_and_forward_feed_data,
                args=(
                    feed_listener,
                    wait_for_twin_creation,
                ),
                daemon=True,
            ).start()

        iotics_api.upsert_twin(
            twin_did=twin_shadow_identity.did,
            properties=twin_shadow_properties,
            feeds=shadow_twin_feeds,
        )

        print(f"Shadow Twin {twin_shadow_identity.did} created")
        wait_for_twin_creation.set()

    # We now just need to wait for new data sent by the Car Twins
    # and forward the data via the related Shadow Twins
    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
