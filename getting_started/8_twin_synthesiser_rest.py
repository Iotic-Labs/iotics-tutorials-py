"""This script aims to show an example of the creation of a Twin Synthesiser that
subscribes to the Twin Publisher's Feed created in exercise #3,
computes the average of the data received and shares it via a Feed.
Run this script while running an instance of the Twin Publisher (exercise #3).
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import List

from helpers.constants import (
    CELSIUS_DEGREES,
    CREATED_BY,
    INDEX_URL,
    LABEL,
    THERMOMETER,
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
from requests import request

HOST_URL: str = ""

AGENT_KEY_NAME: str = ""
AGENT_SEED: str = ""


# For this example is much easier the use of a Class that includes all the methods
# needed for this exercise.
class TwinSynthesiserRestExample:
    def __init__(self):
        self._twin_synthesiser_did: str = None
        self._user_identity: RegisteredIdentity = None
        self._agent_identity: RegisteredIdentity = None
        self._identity_api: HighLevelIdentityApi = None
        self._headers: dict = {
            "accept": "application/json",
            "Iotics-ClientAppId": "twin_synthesiser",
            "Content-Type": "application/json",
        }
        self._token: str = None
        self._stomp_client: StompClient = None

        # The following variables are merely used to compute the average of the data received
        self._sample_count: int = 1
        self._previous_mean: float = 0

    def setup_identities(self, resolver_url: str) -> str:
        self._identity_api = get_rest_high_level_identity_api(resolver_url=resolver_url)

        (
            self._user_identity,
            self._agent_identity,
        ) = self._identity_api.create_user_and_agent_with_auth_delegation(
            user_seed=bytes.fromhex(USER_SEED),
            user_key_name=USER_KEY_NAME,
            agent_seed=bytes.fromhex(AGENT_SEED),
            agent_key_name=AGENT_KEY_NAME,
        )

        self._token: str = self._identity_api.create_agent_auth_token(
            user_did=self._user_identity.did,
            agent_registered_identity=self._agent_identity,
            duration=60,
        )

        self._headers.update({"Authorization": f"Bearer {self._token}"})

    def setup_stomp(self, stomp_url: str):
        self._stomp_client = StompClient(
            stomp_endpoint=stomp_url,
            callback=self.feed_data_callback,
            token=self._token,
        )

    def _share_synthesised_data(self, received_data: dict, twin_synthesiser_did: str):
        # Compute the average
        new_sample = received_data.get("reading")
        new_mean = (
            (self._sample_count - 1) * self._previous_mean + new_sample
        ) / self._sample_count

        # Prepare the data to share
        synth_feed_id: str = "temperature_avg"
        value_label: str = "average"
        data_to_share: dict = {value_label: new_mean}
        encoded_data: str = base64.b64encode(
            json.dumps(data_to_share).encode()
        ).decode()

        data_to_share_payload: dict = {
            "sample": {"data": encoded_data, "mime": "application/json"}
        }

        # Use the Share Feed Data operation
        make_api_call(
            method="POST",
            endpoint=f"{HOST_URL}/qapi/twins/{twin_synthesiser_did}/feeds/{synth_feed_id}/shares",
            headers=self._headers,
            payload=data_to_share_payload,
        )

        print(
            f"Shared {data_to_share} from Twin {twin_synthesiser_did} via Feed {synth_feed_id}"
        )

        # Update the average
        self._previous_mean = new_mean
        self._sample_count += 1

    def feed_data_callback(self, headers, body):
        # This callback allows the Synthesiser Twin to get the data shared by the Twin Publisher
        # and pass it to another function to compute the average and shares it via the Synthesiser's Feed
        encoded_data = json.loads(body)
        followed_twin_did = encoded_data["interest"]["followedFeedId"]["twinId"]
        follower_twin_did = encoded_data["interest"]["followerTwinId"]["id"]

        try:
            time = encoded_data["feedData"]["occurredAt"]
            data = encoded_data["feedData"]["data"]
        except KeyError:
            print("No data")
        else:
            # The following variable includes the (temperature) data sent by the Twin Publisher
            decoded_feed_data = json.loads(base64.b64decode(data).decode("ascii"))
            print(
                f"Received data {decoded_feed_data} from Twin {followed_twin_did} at time {time}"
            )
            self._share_synthesised_data(
                received_data=decoded_feed_data, twin_synthesiser_did=follower_twin_did
            )

    def create_new_twin_identity(self, twin_key_name: str) -> RegisteredIdentity:
        twin_synthesiser_identity: RegisteredIdentity = (
            self._identity_api.create_twin_with_control_delegation(
                twin_key_name=twin_key_name,
                twin_seed=bytes.fromhex(AGENT_SEED),
                agent_registered_identity=self._agent_identity,
            )
        )

        return twin_synthesiser_identity

    def search_twins(self, search_payload: dict) -> List[dict]:
        twins_found_list: List[dict] = []

        search_headers: dict = self._headers.copy()
        search_headers.update(
            {
                "Iotics-RequestTimeout": (
                    datetime.now(tz=timezone.utc) + timedelta(seconds=float(3))
                ).isoformat()
            }
        )

        with request(
            method="POST",
            url=f"{HOST_URL}/qapi/searches",
            headers=search_headers,
            stream=True,
            verify=True,
            params={"scope": "LOCAL"},
            json=search_payload,
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

        return twins_found_list

    def subscribe_to_feed(
        self, twin_follower_did: str, twin_publisher_did: str, feed_id: str
    ):
        print(f"Waiting for data from feed {feed_id}...")

        # Use the STOMP Client to subscribe to the Feed
        subscribe_to_feed_endpoint: str = (
            f"/qapi/twins/{twin_follower_did}/interests/twins/{twin_publisher_did}/feeds/{feed_id}"
        )
        self._stomp_client.subscribe(
            topic=subscribe_to_feed_endpoint,
            subscription_id=f"{twin_publisher_did}-{feed_id}",
        )

    def upsert_twin(
        self, twin_did: str, twin_properties: List[dict], twin_feeds: List[dict]
    ):
        upsert_twin_payload: dict = {
            "twinId": {"id": twin_did},
            "properties": twin_properties,
            "feeds": twin_feeds,
        }

        make_api_call(
            method="PUT",
            endpoint=f"{HOST_URL}/qapi/twins",
            headers=self._headers,
            payload=upsert_twin_payload,
        )


def main():
    twin_synthesiser_rest_obj = TwinSynthesiserRestExample()

    iotics_index: dict = make_api_call(
        method="GET", endpoint=INDEX_URL.format(host_url=HOST_URL)
    )
    resolver_url: str = iotics_index.get("resolver")
    stomp_url: str = iotics_index.get("stomp")

    twin_synthesiser_rest_obj.setup_identities(resolver_url=resolver_url)
    twin_synthesiser_rest_obj.setup_stomp(stomp_url=stomp_url)

    twin_synthesiser_identity: RegisteredIdentity = (
        twin_synthesiser_rest_obj.create_new_twin_identity(
            twin_key_name="TwinSynthesiser"
        )
    )

    # Let's define the metadata description of the Twin Synthesiser
    twin_properties: List[dict] = [
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Twin Synthesiser", "lang": "en"},
        },
        {
            "key": CREATED_BY,
            "stringLiteralValue": {"value": "Michael Joseph Jackson"},
        },
    ]
    # We can now define the (only) Feed used to share average temperature data
    synth_feed_id: str = "temperature_avg"
    value_label: str = "average"
    feed_properties: List[dict] = [
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Average Temperature", "lang": "en"},
        },
    ]
    feed_values: List[dict] = [
        {
            "comment": "Temperature in degrees Celsius",
            "dataType": "integer",
            "label": value_label,
            "unit": CELSIUS_DEGREES,
        }
    ]
    feeds: List[dict] = [
        {
            "id": synth_feed_id,
            "storeLast": True,
            "properties": feed_properties,
            "values": feed_values,
        },
    ]

    # We can use the Upsert Twin operation to create the Twin Synthesiser
    twin_synthesiser_rest_obj.upsert_twin(
        twin_did=twin_synthesiser_identity.did,
        twin_properties=twin_properties,
        twin_feeds=feeds,
    )
    print(f"Twin {twin_synthesiser_identity.did} created")

    # We now need to search for the Twin Publisher implemented in exercise #3
    search_payload: dict = {
        "responseType": "FULL",
        "filter": {
            "text": "publisher",
            "properties": [{"key": TYPE, "uriValue": {"value": THERMOMETER}}],
        },
    }

    twins_found_list = twin_synthesiser_rest_obj.search_twins(
        search_payload=search_payload
    )

    print(f"Found {len(twins_found_list)} twin(s) based on the search criteria")
    print("---")

    # Hopefully there will be only 1 Twin returned by the Search operation
    twin_of_interest: dict = next(iter(twins_found_list))
    # As always, in order to subscribe to a Twin's Feed we need Twin ID and Feed ID
    publisher_twin_id: str = twin_of_interest["twinId"]["id"]
    twin_feeds: List[dict] = twin_of_interest.get("feeds")

    # The Twin Publisher implemented in exercise #3 has only 1 Feed
    feed_of_interest: dict = next(iter(twin_feeds))
    publisher_feed_id: str = feed_of_interest["feedId"]["id"]
    # We can now finally subscribe to its Feed, wait for new data,
    # compute the average and publish it via the Synthesiser Twin's Feed by using
    # the callback function associated to the STOMP Client
    twin_synthesiser_rest_obj.subscribe_to_feed(
        twin_follower_did=twin_synthesiser_identity.did,
        twin_publisher_did=publisher_twin_id,
        feed_id=publisher_feed_id,
    )

    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
