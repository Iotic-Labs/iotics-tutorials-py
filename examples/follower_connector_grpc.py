import json
import logging
import random
import sys
import threading
from time import sleep, time
from typing import List

import grpc
from helpers.constants import (
    PROPERTY_KEY_COLOR,
    PROPERTY_KEY_COMMENT,
    PROPERTY_KEY_CREATED_BY,
    PROPERTY_KEY_FROM_MODEL,
    PROPERTY_KEY_HOST_ALLOW_LIST,
    PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_SPACE_NAME,
    PROPERTY_KEY_TYPE,
    PROPERTY_VALUE_ALLOW_ALL,
    PROPERTY_VALUE_MODEL,
    TOKEN_REFRESH_PERIOD_PERCENT,
    UNIT_DEGREE_CELSIUS,
)
from helpers.identity import Identity
from helpers.identity2 import IdentityHelper2
from iotics.api.common_pb2 import GeoLocation, Property
from iotics.lib.grpc.iotics_api import IoticsApi as IOTICSviagRPC

HOST_URL = "demo.dev.iotics.space:443"
USER_KEY_NAME = "00"
USER_SEED = "a7631ed56882044021224d06c8deb966afb6a5db2115c805900b02c35b8188ce"
AGENT_KEY_NAME = "00"
AGENT_SEED = "e8da559d6197e3160d48c901db985e1b32984c7c72c2613a5e1cf7692e6e6e48"


def auto_refresh_token_grpc(identity: IdentityHelper2, iotics_api: IOTICSviagRPC):
    while True:
        lasted: float = time() - identity.token_last_updated
        # print(identity.token_last_updated, lasted, identity.token_duration, TOKEN_REFRESH_PERIOD_PERCENT)
        if lasted >= identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT:
            identity.refresh_token(duration=10)
            iotics_api.update_channel()


# def receive_and_forward_feed_data(
#     iotics_api: IOTICSviagRPC,
#     shadow_twin_did: str,
#     followed_twin_did: str,
#     feed_id: str,
# ):
#     feed_listener = iotics_api.fetch_interests(
#         follower_twin_did=shadow_twin_did,
#         followed_twin_did=followed_twin_did,
#         followed_feed_id=feed_id,
#     )

#     try:
#         # Receive data from original Supplier Twins
#         for latest_feed_data in feed_listener:
#             data = json.loads(latest_feed_data.payload.feedData.data)
#             print("Received", data)
#     except grpc._channel._MultiThreadedRendezvous:
#         # This exception occurs when the Token expires
#         # If that happens, generate a new token and re-run the function
#         print("Token expired")
#         receive_and_forward_feed_data(
#             iotics_api=iotics_api,
#             shadow_twin_did=shadow_twin_did,
#             followed_twin_did=followed_twin_did,
#             feed_id=feed_id,
#         )
#     except grpc._channel._InactiveRpcError:
#         pass


def follow_original(
    iotics_api: IOTICSviagRPC,
    shadow_twin_did: str,
    original_twin_did: str,
    original_feed_id: str,
    fetch_last_stored: bool = True,
):
    feed_listener = iotics_api.fetch_interests(
        follower_twin_did=shadow_twin_did,
        followed_twin_did=original_twin_did,
        followed_feed_id=original_feed_id,
        fetch_last_stored=fetch_last_stored,
    )

    try:
        for latest_feed_data in feed_listener:
            data_received = json.loads(latest_feed_data.payload.feedData.data)
            print("Received", data_received)
    except grpc._channel._MultiThreadedRendezvous:
        # print("Token expired")
        follow_original(
            iotics_api=iotics_api,
            shadow_twin_did=shadow_twin_did,
            original_twin_did=original_twin_did,
            original_feed_id=original_feed_id,
            fetch_last_stored=False,
        )
    except grpc._channel._InactiveRpcError:
        pass


def main():
    identity_helper = IdentityHelper2(
        resolver_url="https://did.prd.iotics.com", host_url=HOST_URL
    )

    identity_helper.create_user_and_agent_with_auth_delegation(
        user_key_name=USER_KEY_NAME,
        user_seed=USER_SEED,
        agent_key_name=AGENT_KEY_NAME,
        agent_seed=AGENT_SEED,
    )

    identity_helper.refresh_token(duration=10)
    iotics_api = IOTICSviagRPC(auth=identity_helper)

    threading.Thread(
        target=auto_refresh_token_grpc,
        args=(
            identity_helper,
            iotics_api,
        ),
        daemon=True,
    ).start()

    twin_identity = identity_helper.create_twin_with_control_delegation(
        twin_key_name="SensorTwin0", twin_seed=AGENT_SEED
    )

    print("Twin created", twin_identity.did)

    threading.Thread(
        target=follow_original,
        args=(
            iotics_api,
            twin_identity.did,
            "did:iotics:iotNDbzkD4edKdemj1Fr5UJnVdYcg9iB4iLJ",
            "temperature",
        ),
        daemon=True,
    ).start()

    while True:
        try:
            sleep(3)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
