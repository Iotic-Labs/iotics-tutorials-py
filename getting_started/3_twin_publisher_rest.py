"""This script aims to show how to implement a Twin Publisher
that shares a random integer every 5 seconds via REST.
"""
import base64
import json
import sys
from random import randint
from time import sleep
from typing import Optional

from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)
from requests import Response, request

HOST_URL: str = ""  # URL of your IOTICSpace (i.e.: "https://my-space.iotics.space")

# In order to create the following values, you can look at "2_create_user_and_agent.py".
USER_KEY_NAME: str = ""
USER_SEED: str = ""
AGENT_KEY_NAME: str = ""
AGENT_SEED: str = ""


def make_api_call(
    method: str,
    endpoint: str,
    headers: Optional[dict] = None,
    payload: Optional[dict] = None,
) -> dict:
    """This method will simply execute a REST call according to a specific
    method, endpoint and optional headers and payload."""

    try:
        req_resp: Response = request(
            method=method, url=endpoint, headers=headers, json=payload
        )
        req_resp.raise_for_status()
        response: dict = req_resp.json()
    except Exception as ex:
        print("Getting error", ex)
        sys.exit(1)

    return response


def main():
    # Let's retrieve the Resolver URL automatically so we can instantiate an identity api variable
    resolver_url_res: dict = make_api_call(
        method="GET", endpoint=f"{HOST_URL}/index.json"
    )
    resolver_url: str = resolver_url_res.get("resolver")
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

    # In order to use the Upsert Twin operation we need the Host ID.
    # This can be retrieved via the Get Host ID operation.
    # Get Host ID with REST: https://docs.iotics.com/reference/get_host_id
    host_twin_response: dict = make_api_call(
        method="GET",
        endpoint=f"{HOST_URL}/qapi/host/id",
        headers=headers,
    )
    host_twin_did: str = host_twin_response.get("hostId")

    # We now need to create a new Twin Identity which will be used for our Twin Publisher.
    # Only Agents can perform actions against a Twin.
    # This means, after creating the Twin Identity it has to "control-delegate" an Agent Identity
    # so the latter can control the Digital Twin.
    twin_publisher_identity: RegisteredIdentity = identity_api.create_twin_with_control_delegation(
        # The Twin Key Name's concept is the same as Agent and User Key Name
        twin_key_name="TwinPublisher",
        # It is a best-practice to re-use the "AGENT_SEED" as a Twin seed.
        twin_seed=bytes.fromhex(AGENT_SEED),
        agent_registered_identity=agent_identity,
    )

    twin_publisher_did: str = twin_publisher_identity.did

    # We can now use the Upsert Twin operation in order to:
    # 1. Create the Digital Twin;
    # 2. Add Twin's Metadata;
    # 3. Add a Feed object (Feed's Metadata + Feed's Value) to this Twin.
    feed_id: str = "temperature"
    value_label: str = "reading"
    upsert_twin_payload: dict = {
        "twinId": {"hostId": host_twin_did, "id": twin_publisher_did},
        "properties": [
            {
                "key": "http://www.w3.org/2000/01/rdf-schema#label",
                "langLiteralValue": {"value": "Twin Publisher", "lang": "en"},
            }
        ],
        "feeds": [
            {
                "id": feed_id,
                "storeLast": True,
                "properties": [
                    {
                        "key": "http://www.w3.org/2000/01/rdf-schema#label",
                        "langLiteralValue": {"value": "Temperature", "lang": "en"},
                    },
                ],
                "values": [
                    {
                        "comment": "Temperature in degrees Celsius",
                        "dataType": "integer",
                        "label": value_label,
                        "unit": "http://qudt.org/vocab/unit/DEG_C",
                    }
                ],
            },
        ],
    }

    # Upsert Twin with REST: https://docs.iotics.com/reference/upsert_twin
    make_api_call(
        method="PUT",
        endpoint=f"{HOST_URL}/qapi/twins",
        headers=headers,
        payload=upsert_twin_payload,
    )

    print(f"Twin {twin_publisher_did} upserted succesfully")

    # Now that we've created a Twin with a Feed, we can create an infinite loop where we:
    # 1. Generate a random integer;
    # 2. Share the above via the Twin's Feed.
    try:
        while True:
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
                endpoint=f"{HOST_URL}/qapi/hosts/{host_twin_did}/twins/{twin_publisher_did}/feeds/{feed_id}/shares",
                headers=headers,
                payload=data_to_share_payload,
            )

            print(
                f"Shared {data_to_share} from Twin {twin_publisher_did} via Feed {feed_id}"
            )

            sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
