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
from datetime import datetime, timedelta, timezone
from threading import Thread
from time import sleep
from typing import List

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
from helpers.stomp_client import StompClient
from helpers.utilities import make_api_call
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)
from requests import request

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
    identity_api: HighLevelIdentityApi = get_rest_high_level_identity_api(
        resolver_url=resolver_url
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

    token: str = identity_api.create_agent_auth_token(
        user_did=user_identity.did,
        agent_registered_identity=agent_identity,
        duration=60,
    )

    headers: dict = {
        "accept": "application/json",
        "Iotics-ClientAppId": "twin_shadow",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    def feed_data_callback(stomp_headers, body):
        """The Callback we want to define for this exercise will simply
        forward, through the use of the Share Feed Data operation, all the data
        samples received by the "original" Car Twins.
        """

        encoded_data = json.loads(body)

        try:
            followed_twin_id = encoded_data["interest"]["followedFeedId"]["twinId"]
            follower_twin_id = encoded_data["interest"]["followerTwinId"]["id"]
            followed_feed_id = encoded_data["interest"]["followedFeedId"]["id"]
            received_data = encoded_data["feedData"]["data"]
            mime_type = encoded_data["feedData"]["mime"]
            occurred_at = encoded_data["feedData"]["occurredAt"]
        except KeyError:
            print("No data")
        else:
            data_to_share_payload: dict = {
                "sample": {
                    "data": received_data,
                    "mime": mime_type,
                    "occurredAt": occurred_at,
                }
            }

            # Use the Share Feed Data operation
            make_api_call(
                method="POST",
                endpoint=f"{HOST_URL}/qapi/twins/{follower_twin_id}/feeds/{followed_feed_id}/shares",
                headers=headers,
                payload=data_to_share_payload,
            )
            print(f"Forwarded data sample received from Twin {followed_twin_id}")

    stomp_url: str = iotics_index.get("stomp")
    stomp_client: StompClient = StompClient(
        stomp_endpoint=stomp_url, callback=feed_data_callback, token=token
    )

    def subscribe_to_feed(twin_follower_id: str, twin_followed_id: str, feed_id: str):
        """This function will be used for the STOMP Client to subscribe to the feed's endpoint.

        Args:
            twin_follower_id (str): the Twin Follower ID
            twin_followed_id (str): the Twin that is being followed
            feed_id (str): The Feed ID that is sharing data
        """
        subscribe_to_feed_endpoint: str = f"/qapi/twins/{twin_follower_id}/interests/twins/{twin_followed_id}/feeds/{feed_id}"
        stomp_client.subscribe(
            topic=subscribe_to_feed_endpoint,
            subscription_id=f"{twin_followed_id}-{feed_id}",
        )

        print(f"Subscribed to Feed {feed_id} from Twin {twin_follower_id}")

    # We now want to search for the Car Twins created in exercise 10
    search_headers: dict = headers.copy()
    search_headers.update(
        {
            "Iotics-RequestTimeout": (
                datetime.now(tz=timezone.utc) + timedelta(seconds=float(3))
            ).isoformat()
        }
    )

    # We can search for the Car Twins by taking into consideration their Twin Properties.
    # In particular we can use their TYPE property alongside an additional Property, the Created At.
    payload: dict = {
        "responseType": "FULL",
        "filter": {
            "properties": [
                {"key": TYPE, "uriValue": {"value": CAR}},
                {
                    "key": CREATED_BY,
                    "stringLiteralValue": {"value": "Michael Joseph Jackson"},
                },
            ],
        },
    }

    twins_found_list: List[dict] = []

    with request(
        method="POST",
        url=f"{HOST_URL}/qapi/searches",
        headers=search_headers,
        stream=True,
        verify=True,
        params={"scope": "LOCAL"},
        json=payload,
    ) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_lines():
            response = json.loads(chunk)
            twins_found = []
            try:
                twins_found = response["result"]["payload"]["twins"]
            except KeyError:
                continue
            finally:
                if twins_found:
                    twins_found_list.extend(twins_found)

    print(f"Found {len(twins_found_list)} twin(s) based on the search criteria")
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

        car_twin_id: str = car_twin["twinId"]["id"]
        car_twin_properties: List[dict] = car_twin.get("properties")
        # Let's create a list of Properties for the Shadow Twins
        # that will be different from the Car Twins'.
        # Compared to the Car Twins, we want the Shadow Twins' data and metadata to be
        # visible to Twins in other Spaces. This means their Selective Sharing Permission
        # has to be set to Allow All
        twin_shadow_properties: List[dict] = [
            {"key": HOST_ALLOW_LIST, "uriValue": {"value": ALLOW_ALL}},
            {"key": HOST_METADATA_ALLOW_LIST, "uriValue": {"value": ALLOW_ALL}},
        ]

        for car_twin_property in car_twin_properties:
            # We want to avoid adding to the Shadow Twins the list of Property
            # pre-defined in the 'PROPERTY_KEYS_TO_HIDE' list
            if car_twin_property["key"] in PROPERTY_KEYS_TO_HIDE:
                continue

            # The Shadow Twins' label will be equal to the Car Twins'
            # with the addition of the word 'Shadow' at the end.
            if car_twin_property["key"] == LABEL:
                car_twin_property["langLiteralValue"]["value"] += " Shadow"

            # We want to add the remaining Car Twin's Properties to the Shadow Twins'
            twin_shadow_properties.append(car_twin_property)

        car_twin_feeds: List[dict] = car_twin.get("feeds")
        shadow_twin_feeds: List[dict] = []
        threads_list: List[Thread] = []
        # Let's scan all the Car Twins' Feeds so the Shadow Twins can subscribe to
        # and forward the data through them.
        for car_twin_feed in car_twin_feeds:
            feed_id: str = car_twin_feed["feedId"]["id"]
            # We want to avoid the Shadow Twins to replicate the list of Feeds
            # pre-defined in the 'FEED_IDS_TO_HIDE' list
            if feed_id in FEED_IDS_TO_HIDE:
                continue

            # We need to describe the Car Twin's Feed in order to get its structure
            feed_description: dict = make_api_call(
                method="GET",
                endpoint=f"{HOST_URL}/qapi/twins/{car_twin_id}/feeds/{feed_id}",
                headers=headers,
            )

            shadow_twin_feeds.append(
                {
                    "id": feed_id,
                    "storeLast": feed_description["result"]["storeLast"],
                    "properties": feed_description["result"]["properties"],
                    "values": feed_description["result"]["values"],
                }
            )

            # We now need the STOMP Client to subscribe to this Feed,
            # but only after the Shadow Twin is created.
            th = Thread(
                target=subscribe_to_feed,
                args=[twin_shadow_identity.did, car_twin_id, feed_id],
                daemon=True,
            )
            threads_list.append(th)

        upsert_twin_payload: dict = {
            "twinId": {"id": twin_shadow_identity.did},
            "properties": twin_shadow_properties,
            "feeds": shadow_twin_feeds,
        }

        # Use the Upsert Twin operation to create the Shadow Twin with the list of Properties
        # and Feeds defined above
        make_api_call(
            method="PUT",
            endpoint=f"{HOST_URL}/qapi/twins",
            headers=headers,
            payload=upsert_twin_payload,
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
