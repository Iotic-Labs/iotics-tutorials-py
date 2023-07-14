"""This script aims to show an example of:
1. the creation of a Twin Follower;
2. how to search for the Twin Publisher implemented in the exercise #3;
3. how to subscribe to its Feeds to receive Feed's data.
Run this script while running an instance of the Twin Publisher (exercise #3).
"""

import json
import threading
from time import sleep

from helpers.identity_interface import IdentityInterface
from iotics.lib.grpc.helpers import create_property
from iotics.lib.grpc.iotics_api import IoticsApi
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)

from helpers.constants import DEFINES, INDEX_URL, THERMOMETER, USER_KEY_NAME, USER_SEED
from helpers.utilities import make_api_call

HOST_URL: str = ""

AGENT_KEY_NAME: str = ""
AGENT_SEED: str = ""


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
    iotics_api.create_twin(twin_did=twin_follower_did)
    print(f"Twin {twin_follower_did} created")

    # We now want to search for the Twin Publisher implemented in exercise #3.
    # To do that we can use as a search criteria the text='publisher' along with
    # the Ontology that characterises our Twin Publisher, namely 'thermometer'.
    # Be aware, if in the same Host there are other Twins that include these parameters,
    # all of them will be returned by this search.
    search_criteria = iotics_api.get_search_payload(
        properties=[create_property(key=DEFINES, value=THERMOMETER, is_uri=True)],
        text="publisher",
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

    # We now want to define a function that will be used to wait for new data samples
    def get_feed_data(feed_listener, feed_id):
        print(f"Waiting for data from feed {feed_id}...")

        # 'feed_listener' is a blocking function that will wait until a new data sample is received
        for latest_feed_data in feed_listener:
            # When a new data sample is received (in other words sent by the Twin Publisher),
            # then simply decode it and print it on screen.
            # Of course, in advanced application, the following block will contain the logic
            # you want to trigger whenever a new data sample is received (see exercise #8).
            data_received = json.loads(latest_feed_data.payload.feedData.data)
            print(f"Received Feed data {data_received}")

    # Although for this exercise the Search operation might have returned only the Twin Publisher
    # implemented in exercise #3, for completeness we want to scan over the entire list of Twins found.
    for twin in twins_found_list:
        # In order to subscribe to a Twin Publisher's Feed, we need 2 info:
        # - the Twin Publisher ID
        # - the Feed ID that we want to subscribe to
        twin_id = twin.twinId.id
        # The following variable includes the list of Feed IDs belonging to the Twin Publisher
        twin_feeds = twin.feeds

        # Although the Twin Publisher implemented in exercise #3 includes only 1 Feed,
        # for completeness we want to scan all its Feeds and subscribe to each one of them.
        for twin_feed in twin_feeds:
            feed_id = twin_feed.feedId.id
            # We have now all the info we need to subscribe to a Feed: Twin ID and Feed ID.
            # We can now create a 'Feed Listener' that will be used to wait for new data.
            # Be aware, the 'fetch_interests' operation of the gRPC Library includes an optional parameter
            # called 'fetch_last_stored' to get immediately the last value shared by the Twin Publisher.
            # You can set it to False if you only want to get new data samples.
            feed_listener = iotics_api.fetch_interests(
                follower_twin_did=twin_follower_did,
                followed_twin_did=twin_id,
                followed_feed_id=feed_id,
            )

            # Since the 'fetch_interests' returns a blocking function, we can create a Thread
            # to handle the receival of data samples from it so that we can perform other duties.
            threading.Thread(
                target=get_feed_data, args=(feed_listener, feed_id), daemon=True
            ).start()

    # We now just need to wait for new data sent by the Twin Publisher
    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
