"""This script aims to show an example of the creation of a Twin Receiver
with an Input that waits for Input messages.
"""

import base64
import json
from time import sleep
from typing import List

from helpers.constants import (
    CREATED_BY,
    INDEX_URL,
    LABEL,
    LIGHT_BULB,
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
        "Iotics-ClientAppId": "twin_receiver",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    twin_receiver_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(
            twin_key_name="TwinReceiver",
            twin_seed=bytes.fromhex(AGENT_SEED),
            agent_registered_identity=agent_identity,
        )
    )

    twin_receiver_did: str = twin_receiver_identity.did

    # We can define the structure of our Twin Publisher in terms of:
    # - Twin Properties
    # - Inputs
    twin_properties: List[dict] = [
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Twin Receiver", "lang": "en"},
        },
        {
            "key": CREATED_BY,
            "stringLiteralValue": {"value": "Michael Joseph Jackson"},
        },
        # In this example we are virtualising a Light Bulb. So we can use a public ontology
        # that defines the unique meaning of such an object.
        {"key": TYPE, "uriValue": {"value": LIGHT_BULB}},
    ]

    input_id: str = "turn_on"
    value_label: str = "value"
    # Inputs follow the same structure as Feeds in terms of Properties and Values
    input_properties: List[dict] = [
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Turn On", "lang": "en"},
        },
    ]
    input_values: List[dict] = [
        {
            "comment": "Turn ON/OFF Light Bulb",
            "dataType": "boolean",
            "label": value_label,
        }
    ]
    inputs: List[dict] = [
        {"id": input_id, "properties": input_properties, "values": input_values}
    ]

    # We can now use the Upsert Twin operation in order to:
    # 1. Create the Digital Twin;
    # 2. Add Twin's Metadata;
    # 3. Add an Input object (Input's Metadata + Input's Value) to this Twin.
    upsert_twin_payload: dict = {
        "twinId": {"id": twin_receiver_did},
        "properties": twin_properties,
        "inputs": inputs,
    }

    make_api_call(
        method="PUT",
        endpoint=f"{HOST_URL}/qapi/twins",
        headers=headers,
        payload=upsert_twin_payload,
    )

    print(f"Twin {twin_receiver_did} created")

    # Similar to the subscription to a Feed, we now want to define a function that will be used as a callback
    # for new Input messages.
    def input_data_callback(headers, body):
        # When a new Input message is received (in other words sent by the Twin Sender),
        # then simply decode it and print it on screen.
        encoded_data = json.loads(body)

        try:
            time = encoded_data["message"]["occurredAt"]
            data = encoded_data["message"]["data"]
        except KeyError:
            print("No data")
        else:
            decoded_input_data = json.loads(base64.b64decode(data).decode("ascii"))
            print(f"Received input message {decoded_input_data} at time {time}")

    # Same as with the receival of Feed's data, we need to instantiate a STOMP object so we can
    # subscribe to the Input and receive data from it.
    stomp_url: str = iotics_index.get("stomp")
    stomp_client: StompClient = StompClient(
        stomp_endpoint=stomp_url, callback=input_data_callback, token=token
    )

    # Although our Twin has just 1 Input, for completeness we can scan the entire inputs list
    # and subscribe to each one of them
    for twin_input in inputs:
        input_id = twin_input.get("id")

        subscribe_to_input_endpoint: str = (
            f"/qapi/twins/{twin_receiver_did}/inputs/{input_id}"
        )
        stomp_client.subscribe(
            topic=subscribe_to_input_endpoint,
            subscription_id=f"{twin_receiver_did}-{input_id}",
        )

    print("Waiting for Input messages...")

    # We now just need to wait for incoming messages sent by the Twin Sender
    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
