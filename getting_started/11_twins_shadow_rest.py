"""
"""

import json
from datetime import datetime, timedelta, timezone
import threading
from time import sleep
from typing import List

from helpers.constants import (
    ALLOW_ALL,
    CREATED_BY,
    ELECTRIC_ENGINE,
    FUEL_TYPE,
    HOST_ALLOW_LIST,
    HOST_METADATA_ALLOW_LIST,
    INDEX_URL,
    LABEL,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.utilities import make_api_call
from helpers.stomp_client import StompClient
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    get_rest_high_level_identity_api,
    RegisteredIdentity,
)
from requests import request

HOST_URL: str = ""

AGENT_KEY_NAME: str = ""
AGENT_SEED: str = ""

FEED_IDS_TO_HIDE = ["speed"]
PROPERTY_KEYS_TO_HIDE = [CREATED_BY]


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
        "Iotics-ClientAppId": "twin_shadow",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    def feed_data_callback(stomp_headers, body):
        encoded_data = json.loads(body)

        try:
            followed_twin_id = encoded_data["interest"]["followedFeedId"]["twinId"]
            follower_twin_id = encoded_data["interest"]["followerTwinId"]["id"]
            followed_feed_id = encoded_data["interest"]["followedFeedId"]["id"]
            received_data = encoded_data["feedData"]["data"]
            mime_type = encoded_data["feedData"]["mime"]
            occurred_at = encoded_data["feedData"]["occurredAt"]
        except KeyError:
            print("No data")
        else:
            data_to_share_payload: dict = {
                "sample": {
                    "data": received_data,
                    "mime": mime_type,
                    "occurredAt": occurred_at,
                }
            }
            make_api_call(
                method="POST",
                endpoint=f"{HOST_URL}/qapi/twins/{follower_twin_id}/feeds/{followed_feed_id}/shares",
                headers=headers,
                payload=data_to_share_payload,
            )
            print(f"Forwarded data sample received from Twin {followed_twin_id}")

    stomp_url: str = iotics_index.get("stomp")
    stomp_client: StompClient = StompClient(
        stomp_endpoint=stomp_url, callback=feed_data_callback, token=token
    )

    def subscribe_to_feed(
        twin_follower_id: str,
        twin_followed_id: str,
        feed_id: str,
        wait_for_twin_creation: threading.Event,
    ):
        wait_for_twin_creation.wait()

        subscribe_to_feed_endpoint: str = f"/qapi/twins/{twin_follower_id}/interests/twins/{twin_followed_id}/feeds/{feed_id}"
        stomp_client.subscribe(
            topic=subscribe_to_feed_endpoint,
            subscription_id=f"{twin_followed_id}-{feed_id}",
        )

        print(f"Subscribed to Feed {feed_id} from Twin {twin_follower_id}")

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
            "text": "car",
            "properties": [
                {"key": FUEL_TYPE, "uriValue": {"value": ELECTRIC_ENGINE}},
                {
                    "key": CREATED_BY,
                    "stringLiteralValue": {"value": "Michael Joseph Jackson"},
                },
            ],
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

    for count, car_twin in enumerate(twins_found_list):
        twin_shadow_identity: RegisteredIdentity = (
            identity_api.create_twin_with_control_delegation(
                twin_key_name=f"TwinCarShadow{count}",
                twin_seed=bytes.fromhex(AGENT_SEED),
                agent_registered_identity=agent_identity,
            )
        )

        car_twin_id: str = car_twin["twinId"]["id"]
        car_twin_properties: List[dict] = car_twin.get("properties")
        twin_shadow_properties: List[dict] = [
            {"key": HOST_ALLOW_LIST, "uriValue": {"value": ALLOW_ALL}},
            {"key": HOST_METADATA_ALLOW_LIST, "uriValue": {"value": ALLOW_ALL}},
        ]

        for car_twin_property in car_twin_properties:
            if car_twin_property["key"] in PROPERTY_KEYS_TO_HIDE:
                continue

            if car_twin_property["key"] == LABEL:
                car_twin_property["langLiteralValue"]["value"] += " Shadow"

            twin_shadow_properties.append(car_twin_property)

        car_twin_feeds: List[dict] = car_twin.get("feeds")
        shadow_twin_feeds: List[dict] = []
        wait_for_twin_creation: threading.Event = threading.Event()
        for car_twin_feed in car_twin_feeds:
            feed_id: str = car_twin_feed["feedId"]["id"]
            if feed_id in FEED_IDS_TO_HIDE:
                continue

            feed_description: dict = make_api_call(
                method="GET",
                endpoint=f"{HOST_URL}/qapi/twins/{car_twin_id}/feeds/{feed_id}",
                headers=headers,
            )

            shadow_twin_feeds.append(
                {
                    "id": feed_id,
                    "storeLast": feed_description["result"]["storeLast"],
                    "properties": feed_description["result"]["properties"],
                    "values": feed_description["result"]["values"],
                }
            )

            threading.Thread(
                target=subscribe_to_feed,
                args=(
                    twin_shadow_identity.did,
                    car_twin_id,
                    feed_id,
                    wait_for_twin_creation,
                ),
                daemon=True,
            ).start()

        upsert_twin_payload: dict = {
            "twinId": {"id": twin_shadow_identity.did},
            "properties": twin_shadow_properties,
            "feeds": shadow_twin_feeds,
        }

        make_api_call(
            method="PUT",
            endpoint=f"{HOST_URL}/qapi/twins",
            headers=headers,
            payload=upsert_twin_payload,
        )

        print(f"Shadow Twin {twin_shadow_identity.did} created")
        wait_for_twin_creation.set()

    # We now just need to wait for new data sent by the Car Twins
    # and forward the data via the related Shadow Twins
    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
