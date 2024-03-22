"""This script aims to show an example of the Search Twins operation.
In particular it will search for the Twin Publisher implemented in the previous exercise.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import List

from helpers.constants import (
    CREATED_BY,
    INDEX_URL,
    THERMOMETER,
    TYPE,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.utilities import make_api_call, print_property_rest
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
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
        "Iotics-ClientAppId": "search_twins",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # The Search headers require an additional field: "Iotics-RequestTimeout".
    # The latter is used to stop the search request once the timeout is reached
    search_headers: dict = headers.copy()
    search_headers.update(
        {
            "Iotics-RequestTimeout": (
                datetime.now(tz=timezone.utc) + timedelta(seconds=float(3))
            ).isoformat()
        }
    )

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

    # The following variable will be used to append any Twins found by the Search operation
    twins_found_list: List[dict] = []

    # We can now use the Search operation over REST by specifying the 'scope' parameter.
    # The latter defines where to search for Twins, either locally ('LOCAL') in the Space defined by the 'HOST_URL'
    # or globally ('GLOBAL') in the Network.
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
        # Iterates over the response data, one Host at a time
        for chunk in resp.iter_lines():
            response = json.loads(chunk)
            twins_found = []
            try:
                twins_found = response["result"]["payload"]["twins"]
            except KeyError:
                continue
            finally:
                if twins_found:
                    # Append the twins found to the list of twins
                    twins_found_list.extend(twins_found)

    print(f"Found {len(twins_found_list)} twin(s) based on the search criteria")
    print("---")

    for twin in twins_found_list:
        twin_id: str = twin["twinId"]["id"]
        host_id: str = twin["twinId"]["hostId"]
        location: dict = twin.get("location")
        twin_properties: List[dict] = twin.get("properties")

        print(f"Twin ID: {twin_id}")
        print(f"Host ID: {host_id}")

        if location:
            lat: float = location.get("lat")
            lon: float = location.get("lon")
            print("Location:")
            print("   lat:", lat)
            print("   lon:", lon)

        print(f"Twin Properties ({len(twin_properties)}):")
        for twin_property in twin_properties:
            print_property_rest(twin_property)

    # As mentioned in the description above, the Search operation (when response_type = FULL)
    # allows to return the Twin's Metadata along with the list of Feed IDs and Input IDs.
    # However in order to get the Feed's and/or Input's Metadata, the related Describe operation must be used.
    twin_feeds: List[dict] = twin.get("feeds", [])
    print(f"Twin feeds ({len(twin_feeds)}):")

    for twin_feed in twin_feeds:
        feed_id: str = twin_feed["feedId"]["id"]
        print(f"-  Feed ID: {feed_id}")

    # Same as Feeds, in order to get the Input's Metadata, the Describe Input operation must be used.
    twin_inputs: List[dict] = twin.get("inputs", [])
    print(f"Twin Inputs ({len(twin_inputs)}):")

    for twin_input in twin_inputs:
        input_id = twin_input["inputId"]["id"]
        print(f"-  Input ID: {input_id}")

    print("---")


if __name__ == "__main__":
    main()
