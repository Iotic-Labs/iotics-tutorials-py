"""This script aims to show an example of the Search Twins operation.
In particular it will search for the Twin Publisher implemented in the previous exercise.
"""

from helpers.constants import (
    INDEX_URL,
    CREATED_BY,
    THERMOMETER,
    TYPE,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.identity_interface import IdentityInterface
from helpers.utilities import make_api_call, print_property_grpc
from iotics.lib.grpc.helpers import create_property
from iotics.lib.grpc.iotics_api import IoticsApi
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
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

    # We want to execute a Search Twins operation to find the Twin Publisher implemented in the previous exercise.
    # To do that we need to define (1) the search criteria and (2) the type of results we want to get as a response.
    # Regarding (1), there are 3 types of criteria (at least 1 criteria must be chosen):
    # 1. a location with radius: find all the Twins around a specific geographic location;
    # 2. a list of Twin Properties: find all the Twins that include a given list of Twin Properties (with an AND condition among Properties);
    # 3. a string of text: find all the Twins that include one or more keywords within Twin Label or Twin Comment (with an OR condition among words).
    # Regarding (2), the options are (1 must be chosen):
    # 1. Full: return all the details of the Twins found: Twin ID, Host ID, Location, list of Twin Properties, list of Feed IDs, list of Input IDs;
    # 2. Located: return only a subset of details of the Twins found: Twin ID, Host ID, Location;
    # 3. Minimal (default): return only the minimum details of the Twins found: Twin ID, Host ID.
    search_criteria = iotics_api.get_search_payload(
        properties=[
            create_property(key=TYPE, value=THERMOMETER, is_uri=True),
            create_property(key=CREATED_BY, value="Michael Joseph Jackson"),
        ],
        text="publisher",
        response_type="FULL",
    )

    # After defining the search criteria we can now execute the Search operation
    # which blocks the execution of the code and returns an iterator which can be used to get the list of Twins found;.
    # This method requires the following parameters:
    # 1. Client App ID: a simple ID used to bind together request and response;
    # 2. Search Payload: corresponds to the search criteria defined above;
    # 3. Scope (LOCAL by default): defines where to search for Twins, either locally (LOCAL) in the Space defined by the 'HOST_URL'
    #    or globally (GLOBAL) in the Network;
    # 4. The language to conduct text searches in ("en" by default);
    # 5. Timeout (3s by default): time after which the search iterator will stop blocking and listening for more replies.
    twins_found_list = (
        []
    )  # Let's define a list to add all the Twins found by the Search
    for response in iotics_api.search_iter(
        client_app_id="search_twins", payload=search_criteria
    ):
        twins = response.payload.twins
        twins_found_list.extend(twins)

    print(f"Found {len(twins_found_list)} Twin(s) based on the search criteria")
    print("---")

    for twin in twins_found_list:
        twin_id = twin.twinId.id
        host_id = twin.twinId.hostId
        location = twin.location
        twin_properties = twin.properties
        print(f"Twin ID: {twin_id}")
        print(f"Host ID: {host_id}")

        if location:
            lat = location.lat
            lon = location.lon
            print("Location:")
            print("   lat:", lat)
            print("   lon:", lon)

        print(f"Twin Properties ({len(twin_properties)}):")
        for twin_property in twin_properties:
            print_property_grpc(twin_property)

        # As mentioned in the description above, the Search operation (when response_type = FULL)
        # allows to return the Twin's Metadata along with the list of Feed IDs and Input IDs.
        # However in order to get the Feed's and/or Input's Metadata, the related Describe operation must be used.
        twin_feeds = twin.feeds
        print(f"Twin feeds ({len(twin_feeds)}):")

        for twin_feed in twin_feeds:
            feed_id = twin_feed.feedId.id
            print(f"-  Feed ID: {feed_id}")

        # Same as Feeds, in order to get the Input's Metadata, the Describe Input operation must be used.
        twin_inputs = twin.inputs
        print(f"Twin Inputs ({len(twin_inputs)}):")

        for twin_input in twin_inputs:
            input_id = twin_input.inputId.id
            print(f"-  Input ID: {input_id}")

        print("---")


if __name__ == "__main__":
    main()
