"""This script aims to show an example of:
- the creation of a Twin Sender;
- how to search for the Twin Receiver created in exercise #6;
- send Input message to the above.
Run this script while running an instance of the Twin Receiver (exercise #6).
"""

from random import randint
from time import sleep

from helpers.constants import (
    INDEX_URL,
    CREATED_BY,
    TYPE,
    LABEL,
    MOTION_SENSOR,
    LIGHT_BULB,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.identity_interface import IdentityInterface
from helpers.utilities import make_api_call
from iotics.lib.grpc.helpers import create_property
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

    twin_sender_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(
            twin_key_name="TwinSender",
            twin_seed=bytes.fromhex(AGENT_SEED),
            agent_registered_identity=agent_identity,
        )
    )

    twin_sender_did: str = twin_sender_identity.did

    twin_properties = [
        create_property(key=LABEL, value="Twin Sender", language="en"),
        create_property(key=CREATED_BY, value="Michael Joseph Jackson"),
        # In this example we want to virtualise a motion sensor, so we can use as a Twin Property
        # any Ontology that represents such an object
        create_property(key=TYPE, value=MOTION_SENSOR, is_uri=True),
    ]

    # Use the Upsert Twin operation
    iotics_api.upsert_twin(twin_did=twin_sender_did, properties=twin_properties)
    print(f"Twin {twin_sender_did} created")

    # We now need to search for the Twin Receiver.
    # To do that we can use the specific property that defines the Ontology of a Light Bulb
    # (our Twin Receiver represents a Light Bulb) along with the additional keyword of 'receiver'.
    # Be aware even one of the 2 the search criteria can be enough to retrieve the Twin you are looking for.
    search_criteria = iotics_api.get_search_payload(
        properties=[create_property(key=TYPE, value=LIGHT_BULB, is_uri=True)],
        text="receiver",
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

    # Let's get the first Twin of the list (hopefully it should be the one created in exercise #6)
    twin_of_interest = next(iter(twins_found_list))
    # In order to send Input messages we need 3 info:
    # 1. the Twin Receiver ID;
    # 2. the Input ID;
    # 3. although it's not checked (no error is raised), we also need the Input's Value's label
    twin_receiver_did: str = twin_of_interest.twinId.id
    twin_inputs = twin_of_interest.inputs

    # Let's get the only Input the Twin Receiver includes
    input_of_interest = next(iter(twin_inputs))
    input_id: str = input_of_interest.inputId.id
    # Unfortunately, even the 'FULL' result of a Twin Search operation doesn't give us the description of
    # a Twin's Input. This means, in order to get the Input's Value's label (the 3rd info we need)
    # we need to perform an additional operation, namely the Describe Input.
    input_description = iotics_api.describe_input(
        twin_did=twin_receiver_did, input_id=input_id
    )

    input_values = input_description.payload.result.values

    # Take the first (and only) Input's Value of the list
    value_of_interest = next(iter(input_values))
    value_label = value_of_interest.label

    while True:
        try:
            # We want to generate a random boolean that simulates the motion sensor
            rand_motion_detection: bool = bool(randint(0, 1))
            message_to_send: dict = {value_label: rand_motion_detection}

            # Use the Send Input message operation
            iotics_api.send_input_message(
                sender_twin_did=twin_sender_did,
                receiver_twin_did=twin_receiver_did,
                input_id=input_id,
                message=message_to_send,
            )

            print(
                f"Sent Input message {message_to_send} from Twin {twin_sender_did} to Input '{input_id}' of Twin {twin_receiver_did}"
            )
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
