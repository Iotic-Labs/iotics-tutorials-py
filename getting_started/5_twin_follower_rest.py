"""This script aims to show an example of:
1. the creation of a Twin Follower;
2. how to search for the Twin Publisher implemented in the exercise #3;
3. how to subscribe to its Feeds to receive Feed's data.
Run this script while running an instance of the Twin Publisher (exercise #3).
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import List

from helpers.constants import (
    CREATED_BY,
    INDEX_URL,
    THERMOMETER,
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
        "Iotics-ClientAppId": "twin_follower",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # Let's create a Twin Identity for the Twin Follower
    twin_follower_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(
            twin_key_name="TwinFollower",
            twin_seed=bytes.fromhex(AGENT_SEED),
            agent_registered_identity=agent_identity,
        )
    )

    twin_follower_did: str = twin_follower_identity.did

    # Create the actual Digital Twin by using the Identity generated above
    # Create Twin with REST: https://docs.iotics.com/reference/create_twin
    make_api_call(
        method="POST",
        endpoint=f"{HOST_URL}/qapi/twins",
        headers=headers,
        payload={"id": twin_follower_did},
    )
    print(f"Twin {twin_follower_did} created")

    # We now want to search for the Twin Publisher implemented in exercise #3.
    # To do that we can use as a search criteria the text='publisher' along with
    # the Ontology that characterises our Twin Publisher, namely 'thermometer'.
    # Be aware, if in the same Host there are other Twins that include these parameters,
    # all of them will be returned by this search.
    search_headers: dict = headers.copy()
    search_headers.update(
        {
            "Iotics-RequestTimeout": (
                datetime.now(tz=timezone.utc) + timedelta(seconds=float(3))
            ).isoformat()
        }
    )

    payload: dict = {
        "responseType": "FULL",
        "filter": {
            "text": "publisher",
            "properties": [
                {"key": TYPE, "uriValue": {"value": THERMOMETER}},
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

    # We now want to define a function that will be used as a callback for new data samples
    def feed_data_callback(headers, body):
        encoded_data = json.loads(body)

        try:
            # 'time' includes the datetime the data was shared by the Twin Publisher
            followed_twin_id = encoded_data["interest"]["followedFeedId"]["twinId"]
            follower_twin_id = encoded_data["interest"]["followerTwinId"]["id"]
            followed_feed_id = encoded_data["interest"]["followedFeedId"]["id"]
            received_data = encoded_data["feedData"]["data"]
            mime_type = encoded_data["feedData"]["mime"]
            occurred_at = encoded_data["feedData"]["occurredAt"]
        except KeyError:
            print("No data")
        else:
            # When a new data sample is received (in other words sent by the Twin Publisher),
            # we simply decode it and print it on screen.
            # In advanced applications, this section will contain the logic
            # you want to trigger whenever a new data sample is received (see exercise #8).
            decoded_feed_data = json.loads(
                base64.b64decode(received_data).decode("ascii")
            )
            print(
                f"Received Feed data {received_data} published by Twin {followed_twin_id} via Feed {followed_feed_id}"
            )

    # In order to subscribe to a Feed (or an Input) via REST, the only way is to use STOMP.
    # STOMP defines a protocol for clients and servers to communicate with messaging semantics.
    # We provide a library in Python to help you using it. What you need is:
    # 1. the STOMP endpoint for your Space, which you can retrieve from '<space_url>/index.json';
    # 2. the IOTICS token (be aware you need to make sure to renew it if it expires);
    # 3. a callback to be executed when a new message is received.
    # 4. an object of 'StompClient' that includes all the above
    stomp_url: str = iotics_index.get("stomp")
    stomp_client: StompClient = StompClient(
        stomp_endpoint=stomp_url, callback=feed_data_callback, token=token
    )

    # Although for this exercise the Search operation might have returned only the Twin Publisher
    # implemented in exercise #3, for completeness we want to scan over the entire list of Twins found.
    for twin in twins_found_list:
        # In order to subscribe to a Twin Publisher's Feed, we need 2 info:
        # - the Twin Publisher ID
        # - the Feed ID that we want to subscribe to
        twin_id: str = twin["twinId"]["id"]
        # The following variable includes the list of Feed IDs belonging to the Twin Publisher
        twin_feeds: List[dict] = twin.get("feeds")

        # Although the Twin Publisher implemented in exercise #3 includes only 1 Feed,
        # for completeness we want to scan all its Feeds and subscribe to each one of them.
        for twin_feed in twin_feeds:
            feed_id: str = twin_feed["feedId"]["id"]

            print(f"Waiting for data from feed {feed_id}...")

            # We have now all the info we need to subscribe to a Feed: Twin ID and Feed ID.
            # We can now use the STOMP Client object to subscribe to the endpoint.
            subscribe_to_feed_endpoint: str = (
                f"/qapi/twins/{twin_follower_did}/interests/twins/{twin_id}/feeds/{feed_id}"
            )
            stomp_client.subscribe(
                topic=subscribe_to_feed_endpoint, subscription_id=f"{twin_id}-{feed_id}"
            )

    # We now just need to wait for new data sent by the Twin Publisher
    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
