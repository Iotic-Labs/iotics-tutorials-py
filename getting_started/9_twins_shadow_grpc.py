"""Twins Shadow are Twins that virtualise other Twins. They are generally used to:
-   provide a stub or a simulation of an existing Twin;
-   throttle or anonymise the data published;
-   to partition security and access control to feeds and Metadata selectively.
In particular this script will create 10 Shadow Twins which will receive and forward the data published by the
Car Twins created in exercise 10. They will include the same Metadata and Feeds as the Car Twins except some.
Furtheremore the Selective Sharing Permission of these Shadow Twins will be set to "Allow All". This way
Twins in other Spaces will be able to subscribe to the Shadow Twins' Feeds (but not to the Car Twins',
which will remain invisible).
"""

import json
from threading import Thread
from time import sleep
from typing import List

import grpc
from helpers.constants import (
    ALLOW_ALL,
    CAR,
    CREATED_BY,
    HOST_ALLOW_LIST,
    HOST_METADATA_ALLOW_LIST,
    INDEX_URL,
    LABEL,
    TYPE,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.identity_interface import IdentityInterface
from helpers.utilities import make_api_call
from iotics.lib.grpc.helpers import create_feed_with_meta, create_property
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

    def receive_and_forward_feed_data(feed_listener):
        """The Callback we want to define for this exercise will simply
        forward, through the use of the Share Feed Data operation, all the data
        samples received by the "original" Car Twins.
        """

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
                    # Use the Share Feed Data operation
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

    # We now want to search for the Car Twins created in exercise 10.
    # We can search for the Car Twins by taking into consideration their Twin Properties.
    # In particular we can use their TYPE property alongside an additional Property, the Created At.
    search_criteria = iotics_api.get_search_payload(
        properties=[
            create_property(key=TYPE, value=CAR, is_uri=True),
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

    # For any Car Twin found we want to create a Twin Shadow of it
    for count, car_twin in enumerate(twins_found_list):
        # Let's start by created a new Twin Registered Identity
        twin_shadow_identity: RegisteredIdentity = (
            identity_api.create_twin_with_control_delegation(
                twin_key_name=f"TwinCarShadow{count}",
                twin_seed=bytes.fromhex(AGENT_SEED),
                agent_registered_identity=agent_identity,
            )
        )

        car_twin_id: str = car_twin.twinId.id
        car_twin_properties: List[dict] = car_twin.properties
        # Let's create a list of Properties for the Shadow Twins
        # that will be different from the Car Twins'.
        # Compared to the Car Twins, we want the Shadow Twins' data and metadata to be
        # visible to Twins in other Spaces. This means their Selective Sharing Permission
        # has to be set to Allow All
        twin_shadow_properties: List[dict] = [
            create_property(key=HOST_ALLOW_LIST, value=ALLOW_ALL, is_uri=True),
            create_property(key=HOST_METADATA_ALLOW_LIST, value=ALLOW_ALL, is_uri=True),
        ]

        for car_twin_property in car_twin_properties:
            # We want to avoid adding to the Shadow Twins the list of Property
            # pre-defined in the 'PROPERTY_KEYS_TO_HIDE' list
            if car_twin_property.key in PROPERTY_KEYS_TO_HIDE:
                continue

            # The Shadow Twins' label will be equal to the Car Twins'
            # with the addition of the word 'Shadow' at the end.
            if car_twin_property.key == LABEL:
                car_twin_property.langLiteralValue.value += " Shadow"

            # We want to add the remaining Car Twin's Properties to the Shadow Twins'
            twin_shadow_properties.append(car_twin_property)

        car_twin_feeds: List[dict] = car_twin.feeds
        shadow_twin_feeds: List[dict] = []
        threads_list: List[Thread] = []
        # Let's scan all the Car Twins' Feeds so the Shadow Twins can subscribe to
        # and forward the data through them.
        for car_twin_feed in car_twin_feeds:
            feed_id: str = car_twin_feed.feedId.id
            # We want to avoid the Shadow Twins to replicate the list of Feeds
            # pre-defined in the 'FEED_IDS_TO_HIDE' list
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

            # We need to describe the Car Twin's Feed in order to get its structure
            feed_listener = iotics_api.fetch_interests(
                follower_twin_did=twin_shadow_identity.did,
                followed_twin_did=car_twin_id,
                followed_feed_id=feed_id,
            )

            # We now need the Shadow Twin to subscribe to this Feed,
            # but only after the Shadow Twin is created.
            th = Thread(
                target=receive_and_forward_feed_data, args=[feed_listener], daemon=True
            )
            threads_list.append(th)

        # Use the Upsert Twin operation to create the Shadow Twin with the list of Properties
        # and Feeds defined above
        iotics_api.upsert_twin(
            twin_did=twin_shadow_identity.did,
            properties=twin_shadow_properties,
            feeds=shadow_twin_feeds,
        )

        print(f"Shadow Twin {twin_shadow_identity.did} created")

        # We can now start the Threads in order to subscribe to the Car Twins' Feeds
        # and forward the data received
        for th in threads_list:
            th.start()

    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
