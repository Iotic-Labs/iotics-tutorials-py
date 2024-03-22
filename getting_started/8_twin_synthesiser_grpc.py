"""This script aims to show an example of the creation of a Twin Synthesiser that
subscribes to the Twin Publisher's Feed created in exercise #3,
computes the average of the data received and shares it via a Feed.
Run this script while running an instance of the Twin Publisher (exercise #3).
"""

import json

import grpc
from helpers.constants import (
    CELSIUS_DEGREES,
    CREATED_BY,
    INDEX_URL,
    LABEL,
    THERMOMETER,
    TYPE,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.identity_interface import IdentityInterface
from helpers.utilities import make_api_call
from iotics.lib.grpc.helpers import create_feed_with_meta, create_property, create_value
from iotics.lib.grpc.iotics_api import IoticsApi
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)

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

    twin_synthesiser_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(
            twin_key_name="TwinSynthesiser",
            twin_seed=bytes.fromhex(AGENT_SEED),
            agent_registered_identity=agent_identity,
        )
    )

    twin_synthesiser_did: str = twin_synthesiser_identity.did

    # Let's define the metadata description of the Twin Synthesiser
    twin_properties = [
        create_property(key=LABEL, value="Twin Synthesiser", language="en"),
        create_property(key=CREATED_BY, value="Michael Joseph Jackson"),
    ]

    # We can now define the (only) Feed used to share average temperature data
    synthesiser_feed_id: str = "temperature_avg"
    value_label: str = "average"
    feed_properties = [
        create_property(key=LABEL, value="Average Temperature", language="en")
    ]
    feed_values = [
        create_value(
            label=value_label,
            comment="Temperature in degrees Celsius",
            data_type="integer",
            unit=CELSIUS_DEGREES,
        )
    ]

    feeds = [
        create_feed_with_meta(
            feed_id=synthesiser_feed_id, properties=feed_properties, values=feed_values
        )
    ]

    # We can use the Upsert Twin operation to create the Twin Synthesiser
    iotics_api.upsert_twin(
        twin_did=twin_synthesiser_did, properties=twin_properties, feeds=feeds
    )

    print(f"Twin {twin_synthesiser_did} created")

    # We now need to search for the Twin Publisher implemented in exercise #3
    search_criteria = iotics_api.get_search_payload(
        properties=[create_property(key=TYPE, value=THERMOMETER, is_uri=True)],
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

    # Hopefully there will be only 1 Twin returned by the Search operation
    twin_of_interest = next(iter(twins_found_list))
    # As always, in order to subscribe to a Twin's Feed we need Twin ID and Feed ID
    publisher_twin_id = twin_of_interest.twinId.id
    twin_feeds = twin_of_interest.feeds

    feed_of_interest = next(iter(twin_feeds))
    publisher_feed_id = feed_of_interest.feedId.id

    # Let's create a Feed listener to wait for new data
    feed_listener = iotics_api.fetch_interests(
        follower_twin_did=twin_synthesiser_did,
        followed_twin_did=publisher_twin_id,
        followed_feed_id=publisher_feed_id,
    )

    print(f"Waiting for data from feed {publisher_feed_id}...")

    # The following variables will be used to store the values needed to compute the average
    sample_count: int = 1
    previous_mean: float = 0

    try:
        for latest_feed_data in feed_listener:
            # The following variable includes the (temperature) data sent by the Twin Publisher
            data_received: dict = json.loads(latest_feed_data.payload.feedData.data)
            print(f"Received Feed data {data_received}")

            # Compute the average of the temperatures received so far
            new_sample = data_received.get("reading")
            new_mean = ((sample_count - 1) * previous_mean + new_sample) / sample_count

            data_to_share: dict = {value_label: new_mean}
            # Use the Share Feed Data operation
            iotics_api.share_feed_data(
                twin_did=twin_synthesiser_did,
                feed_id=synthesiser_feed_id,
                data=data_to_share,
            )

            print(
                f"Shared {data_to_share} from Twin {twin_synthesiser_did} via Feed {synthesiser_feed_id}"
            )

            # Update the average
            sample_count += 1
            previous_mean = new_mean
    except grpc._channel._MultiThreadedRendezvous:
        print("Token expired")


if __name__ == "__main__":
    main()
