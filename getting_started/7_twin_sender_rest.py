"""This script aims to show an example of:
- the creation of a Twin Sender;
- how to search for the Twin Receiver created in exercise #6;
- send Input message to the above.
Run this script while running an instance of the Twin Receiver (exercise #6).
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from random import randint
from time import sleep
from typing import List

from helpers.constants import (
    CREATED_BY,
    INDEX_URL,
    LABEL,
    LIGHT_BULB,
    MOTION_SENSOR,
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
        "Iotics-ClientAppId": "twin_sender",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    twin_sender_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(
            twin_key_name="TwinSender",
            twin_seed=bytes.fromhex(AGENT_SEED),
            agent_registered_identity=agent_identity,
        )
    )

    twin_sender_did: str = twin_sender_identity.did

    twin_properties: List[dict] = [
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Twin Sender", "lang": "en"},
        },
        {
            "key": CREATED_BY,
            "stringLiteralValue": {"value": "Michael Joseph Jackson"},
        },
        # In this example we want to virtualise a motion sensor, so we can use as a Twin Property
        # any Ontology that represents such an object
        {"key": TYPE, "uriValue": {"value": MOTION_SENSOR}},
    ]

    upsert_twin_payload: dict = {
        "twinId": {"id": twin_sender_did},
        "properties": twin_properties,
    }

    # Use the Upsert Twin operation
    make_api_call(
        method="PUT",
        endpoint=f"{HOST_URL}/qapi/twins",
        headers=headers,
        payload=upsert_twin_payload,
    )
    print(f"Twin {twin_sender_did} created")

    # We now need to search for the Twin Receiver.
    # To do that we can use the specific property that defines the Ontology of a Light Bulb
    # (our Twin Receiver represents a Light Bulb) along with the additional keyword of 'receiver'.
    # Be aware even one of the 2 the search criteria can be enough to retrieve the Twin you are looking for.
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
            "text": "receiver",
            "properties": [{"key": TYPE, "uriValue": {"value": LIGHT_BULB}}],
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

    # Let's get the first Twin of the list (hopefully it should be the one created in exercise #6)
    twin_of_interest: dict = next(iter(twins_found_list))
    # In order to send Input messages we need 3 info:
    # 1. the Twin Receiver ID;
    # 2. the Input ID;
    # 3. although it's not checked (no error is raised), we also need the Input's Value's label
    twin_receiver_did: str = twin_of_interest["twinId"]["id"]
    twin_inputs: List[dict] = twin_of_interest.get("inputs")

    # Let's get the only Input the Twin Receiver includes
    input_of_interest: dict = next(iter(twin_inputs))
    input_id: str = input_of_interest["inputId"]["id"]
    # Unfortunately, even the 'FULL' result of a Twin Search operation doesn't give us the description of
    # a Twin's Input. This means, in order to get the Input's Value's label (the 3rd info we need)
    # we need to perform an additional operation, namely the Describe Input.
    # Describe Input with REST: https://docs.iotics.com/reference/describe_input_local
    input_description: dict = make_api_call(
        method="GET",
        endpoint=f"{HOST_URL}/qapi/twins/{twin_receiver_did}/inputs/{input_id}",
        headers=headers,
    )

    input_values: List[dict] = input_description["result"]["values"]

    # Take the first (and only) Input's Value of the list
    value_of_interest: dict = next(iter(input_values))
    value_label: str = value_of_interest.get("label")

    while True:
        try:
            # We want to generate a random boolean that simulates the motion sensor
            rand_motion_detection: bool = bool(randint(0, 1))
            # The data needs to be prepared as a dictionary where all the keys have to reflect the values' label
            message_to_send: dict = {value_label: rand_motion_detection}
            # Next step is to convert the data into JSON and encode it using base64
            encoded_data: str = base64.b64encode(
                json.dumps(message_to_send).encode()
            ).decode()
            # Last step is to prepare the payload that will be sent via the REST API
            message_to_send_payload: dict = {
                "message": {"data": encoded_data, "mime": "application/json"}
            }

            # Send a message to an input with REST: https://docs.iotics.com/reference/send_input_message_local
            make_api_call(
                method="POST",
                endpoint=f"{HOST_URL}/qapi/twins/{twin_sender_did}/interests/twins/{twin_receiver_did}/inputs/{input_id}/messages",
                headers=headers,
                payload=message_to_send_payload,
            )

            print(
                f"Sent Input message {message_to_send} from Twin {twin_sender_did} to Input '{input_id}' of Twin {twin_receiver_did}"
            )
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
