"""This script aims to show an example of a Twin Publisher
that virtualises a Temperature sensor and shares a random integer every 5 seconds.
"""

import base64
import json
from random import randint
from time import sleep
from typing import List

from helpers.constants import (
    CELSIUS_DEGREES,
    CREATED_BY,
    INDEX_URL,
    LABEL,
    LONDON_LAT,
    LONDON_LON,
    THERMOMETER,
    TYPE,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.utilities import make_api_call
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)

HOST_URL: str = ""  # URL of your IOTICSpace (i.e.: "https://my-space.iotics.space")

# In order to create the following values, you can look at "2_create_user_and_agent.py".
AGENT_KEY_NAME: str = ""
AGENT_SEED: str = ""


def main():
    # Let's retrieve the Resolver URL automatically so we can instantiate an identity api variable
    iotics_index: dict = make_api_call(
        method="GET", endpoint=INDEX_URL.format(host_url=HOST_URL)
    )
    resolver_url: str = iotics_index.get("resolver")
    identity_api: HighLevelIdentityApi = get_rest_high_level_identity_api(
        resolver_url=resolver_url
    )

    # A User and an Agent Identity need to be created with Authentication Delegation so you can:
    # 1. Create Twin Identities;
    # 2. Generate a Token to use the IOTICS API.
    # Be aware that, if Key Name and Seed don't change, multiple calls of the following function
    # will not create new Identities, it will retrieve the existing ones.
    user_identity: RegisteredIdentity
    agent_identity: RegisteredIdentity
    (
        user_identity,
        agent_identity,
    ) = identity_api.create_user_and_agent_with_auth_delegation(
        user_seed=bytes.fromhex(USER_SEED),
        user_key_name=USER_KEY_NAME,
        agent_seed=bytes.fromhex(AGENT_SEED),
        agent_key_name=AGENT_KEY_NAME,
    )

    # Any IOTICS operation requires a token (JWT). The latter can be created using:
    # 1. A User DID;
    # 2. An Agent Identity;
    # 3. A duration (in seconds)
    # This token will only be valid for the duration expressed on point 3 above.
    # When the token expires you won't be able to use the API so you need to generate a new token.
    # Please remember that the longer the token's duration, the less secure your Twins are.
    # (The token may be stolen and a malicious user can use your Twins on your behalf).
    token: str = identity_api.create_agent_auth_token(
        user_did=user_identity.did,
        agent_registered_identity=agent_identity,
        duration=60,
    )

    headers: dict = {
        "accept": "application/json",
        "Iotics-ClientAppId": "twin_publisher",  # Namespace used to group all the requests/responses
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",  # This is where the token will be used
    }

    # We now need to create a new Twin Identity which will be used for our Twin Publisher.
    # Only Agents can perform actions against a Twin.
    # This means, after creating the Twin Identity it has to "control-delegate" an Agent Identity
    # so the latter can control the Digital Twin.
    twin_publisher_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(
            # The Twin Key Name's concept is the same as Agent and User Key Name
            twin_key_name="TwinPublisher",
            # It is a best-practice to re-use the "AGENT_SEED" as a Twin seed.
            twin_seed=bytes.fromhex(AGENT_SEED),
            agent_registered_identity=agent_identity,
        )
    )

    twin_publisher_did: str = twin_publisher_identity.did

    # We can now define the structure of our Twin Publisher in terms of:
    # - Location
    # - Twin Properties
    # - Feeds
    twin_location: dict = {"lat": LONDON_LAT, "lon": LONDON_LON}
    twin_properties: List[dict] = [
        # 'Label' represents a short human-readable name for the Twin
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Twin Publisher", "lang": "en"},
        },
        # 'Created By' represents the name of the User that creates the Twin
        {
            "key": CREATED_BY,
            "stringLiteralValue": {"value": "Michael Joseph Jackson"},
        },
        # 'Type' provides a way to associate a specific Ontology to a Twin
        # In this example our Twin virtualises a thermometer, so in order to be
        # globally (by humans and machines) and uniquely recognised as such, we can use
        # a publicly available Ontology.
        {"key": TYPE, "uriValue": {"value": THERMOMETER}},
    ]
    feed_id: str = "temperature"
    value_label: str = "reading"
    # Even the Feed needs to be semantically described. That's why its object includes
    # a list of Properties that follow the same principles as the Twin Properties.
    feed_properties: List[dict] = [
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Temperature", "lang": "en"},
        },
    ]

    # Feed values represent the payload the Twin will share.
    # In particular it can be represented with:
    # - a 'label' representing the name of the data sample;
    # - an optional 'comment' representing a long description of the data sample;
    # - a 'dataType' representing the type of the data to be sent (integer, float, string, etc.);
    # - an optional 'unit' representing the URI of unity of measure of the data.
    feed_values: List[dict] = [
        {
            "comment": "Temperature in degrees Celsius",
            "dataType": "integer",
            "label": value_label,
            "unit": CELSIUS_DEGREES,
        }
    ]
    # We can now build the list of Feeds (only 1 item in this example) to be attached to our Twin Publisher
    feeds: List[dict] = [
        {
            "id": feed_id,
            "storeLast": True,  # Whether to store the last data sent
            "properties": feed_properties,
            "values": feed_values,
        },
    ]

    # We can now use the Upsert Twin operation in order to:
    # 1. Create the Digital Twin;
    # 2. Add Twin's Metadata;
    # 3. Add a Feed object (Feed's Metadata + Feed's Value) to this Twin.
    upsert_twin_payload: dict = {
        "twinId": {"id": twin_publisher_did},
        "location": twin_location,
        "properties": twin_properties,
        "feeds": feeds,
    }

    # Upsert Twin with REST: https://docs.iotics.com/reference/upsert_twin
    make_api_call(
        method="PUT",
        endpoint=f"{HOST_URL}/qapi/twins",
        headers=headers,
        payload=upsert_twin_payload,
    )

    print(f"Twin {twin_publisher_did} created")

    # Now that we've created a Twin with a Feed, we can create an infinite loop where we:
    # 1. Generate a random integer;
    # 2. Share the above via the Twin's Feed.
    while True:
        try:
            rand_temperature: int = randint(
                0, 30
            )  # Generate a random integer from 0 to 30
            # The data needs to be prepared as a dictionary where all the keys have to reflect the values' label
            data_to_share: dict = {value_label: rand_temperature}
            # Next step is to convert the data into JSON and encode it using base64
            encoded_data: str = base64.b64encode(
                json.dumps(data_to_share).encode()
            ).decode()
            # Last step is to prepare the payload that needs to be sent via the REST API
            data_to_share_payload: dict = {
                "sample": {"data": encoded_data, "mime": "application/json"}
            }

            # Share Feed Data with REST: https://docs.iotics.com/reference/share_feed_data
            make_api_call(
                method="POST",
                endpoint=f"{HOST_URL}/qapi/twins/{twin_publisher_did}/feeds/{feed_id}/shares",
                headers=headers,
                payload=data_to_share_payload,
            )

            print(
                f"Shared {data_to_share} from Twin {twin_publisher_did} via Feed {feed_id}"
            )

            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
