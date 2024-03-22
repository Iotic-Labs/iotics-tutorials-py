"""This script aims to show an example of the creation of a Twin Receiver
with an Input that waits for Input messages.
"""

import json
from threading import Thread
from time import sleep

from helpers.constants import (
    CREATED_BY,
    TYPE,
    INDEX_URL,
    LABEL,
    LIGHT_BULB,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.identity_interface import IdentityInterface
from helpers.utilities import make_api_call
from iotics.lib.grpc.helpers import (
    create_input_with_meta,
    create_property,
    create_value,
)
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
    twin_properties = [
        create_property(key=LABEL, value="Twin Receiver", language="en"),
        create_property(key=CREATED_BY, value="Michael Joseph Jackson"),
        # In this example we are virtualising a Light Bulb. So we can use a public ontology
        # that defines the unique meaning of such an object.
        create_property(key=TYPE, value=LIGHT_BULB, is_uri=True),
    ]

    input_id: str = "turn_on"
    value_label: str = "value"
    # Inputs follow the same structure as Feeds in terms of Properties and Values
    input_properties = [create_property(key=LABEL, value="Turn On", language="en")]
    input_values = [
        create_value(
            label=value_label, comment="Turn ON/OFF Light Bulb", data_type="boolean"
        )
    ]

    inputs = [
        create_input_with_meta(
            input_id=input_id, properties=input_properties, values=input_values
        )
    ]

    # We can now use the Upsert Twin operation in order to:
    # 1. Create the Digital Twin;
    # 2. Add Twin's Metadata;
    # 3. Add an Input object (Input's Metadata + Input's Value) to this Twin.
    iotics_api.upsert_twin(
        twin_did=twin_receiver_did, properties=twin_properties, inputs=inputs
    )

    print(f"Twin {twin_receiver_did} created")

    # Similar to the subscription to a Feed, we now want to define a function that will be used to wait
    # for new Input messages.
    def get_input_data(input_listener, input_id):
        # When a new Input message is received (in other words sent by the Twin Sender),
        # then simply decode it and print it on screen.
        print(f"Waiting for Input data from input {input_id}...")

        for latest_input_data in input_listener:
            data_received = json.loads(latest_input_data.payload.message.data)
            print(f"Received Input data {data_received}")

    # Although our Twin has just 1 Input, for completeness we can scan the entire inputs list
    # and subscribe to each one of them
    for twin_input in inputs:
        input_id = twin_input.id

        input_listener = iotics_api.receive_input_messages(
            twin_did=twin_receiver_did, input_id=input_id
        )

        Thread(
            target=get_input_data, args=[input_listener, input_id], daemon=True
        ).start()

    # We now just need to wait for incoming messages sent by the Twin Sender
    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
