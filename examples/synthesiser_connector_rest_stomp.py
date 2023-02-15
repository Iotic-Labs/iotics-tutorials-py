import base64
import json
import logging
import sys
import threading
from time import sleep
from typing import List

from helpers.constants import (
    PROPERTY_KEY_COMMENT,
    PROPERTY_KEY_CREATED_BY,
    PROPERTY_KEY_LABEL,
    SUBSCRIBE_TO_FEED,
    UNIT_DEGREE_CELSIUS,
)
from helpers.identity import Identity
from helpers.rest_client import RestClient
from helpers.stomp_client import StompClient
from helpers.utilities import auto_refresh_token_rest_stomp, get_host_endpoints

HOST_URL = ""
USER_KEY_NAME = ""
USER_SEED = ""
AGENT_KEY_NAME = ""
AGENT_SEED = ""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class SynthesiserRestStomp:
    def __init__(self):
        self._identity: Identity = None
        self._rest_client: RestClient = None
        self._stomp_client: StompClient = None
        self._host_id: str = None
        self._previous_mean: int = 0
        self._sample_count: int = 1
        self._twin_synthesiser_did: str = None

        self._setup()

    def _setup(self):
        endpoints = get_host_endpoints(host_url=HOST_URL)
        self._identity = Identity(
            resolver_url=endpoints["resolver"],
            grpc_endpoint=endpoints["grpc"],
            user_key_name=USER_KEY_NAME,
            user_seed=USER_SEED,
            agent_key_name=AGENT_KEY_NAME,
            agent_seed=AGENT_SEED,
        )
        token = self._identity.get_token()
        self._rest_client = RestClient(token=token, host_url=HOST_URL)

        self._stomp_client = StompClient(
            stomp_endpoint=endpoints["stomp"],
            callback=self._follow_callback,
            token=token,
        )

        threading.Thread(
            target=auto_refresh_token_rest_stomp,
            args=(
                self._identity,
                self._rest_client,
                self._stomp_client,
            ),
            daemon=True,
        ).start()

        self._host_id = self._rest_client.get_host_id()

    @property
    def local_host_id(self) -> str:
        return self._host_id

    def create_new_twin(
        self, twin_key_name: str, properties: List[dict], feeds: List[dict] = None
    ):
        twin_identity = self._identity.create_twin_with_control_delegation(
            twin_key_name=twin_key_name
        )

        self._twin_synthesiser_did = twin_identity.did

        self._rest_client.upsert_twin(
            twin_did=self._twin_synthesiser_did,
            host_id=self._host_id,
            properties=properties,
            feeds=feeds,
        )

    def search_publisher_twins(self, properties: List[dict] = None):
        twins_found = self._rest_client.search_twins(properties=properties)

        return twins_found

    def follow_feeds(self, twins_found: list[dict]):
        for twin in twins_found:
            twin_publisher_did = twin["twinId"]["id"]
            twin_publisher_feeds = twin["feeds"]
            for feed in twin_publisher_feeds:
                feed_id = feed["feedId"]["id"]
                self._stomp_client.subscribe(
                    topic=SUBSCRIBE_TO_FEED.url.format(
                        twin_follower_host_id=self._host_id,
                        twin_follower_did=self._twin_synthesiser_did,
                        twin_publisher_host_id=self._host_id,
                        twin_publisher_did=twin_publisher_did,
                        feed_id=feed_id,
                    ),
                    subscription_id=f"{twin_publisher_did}-{feed_id}",
                )

                logging.info(
                    "Subscribed to Feed %s of Twin %s", feed_id, twin_publisher_did
                )

    def _synthesise_data(self, received_data: dict):
        new_sample = received_data["reading"]
        new_mean = (
            (self._sample_count - 1) * self._previous_mean + new_sample
        ) / self._sample_count

        self._rest_client.share_data(
            publisher_twin_did=self._twin_synthesiser_did,
            host_id=self._host_id,
            feed_id="avg_temperature",
            data_to_share={"average": new_mean},
        )

    def _follow_callback(self, headers, body):
        encoded_data = json.loads(body)
        twin_did = encoded_data["interest"]["followedFeedId"]["twinId"]

        try:
            time = encoded_data["feedData"]["occurredAt"]
            data = encoded_data["feedData"]["data"]
        except KeyError:
            logging.error("No data")
        else:
            decoded_feed_data = json.loads(base64.b64decode(data).decode("ascii"))
            logging.info(
                "Received %s from Twin %s at time %s", decoded_feed_data, twin_did, time
            )
            self._synthesise_data(received_data=decoded_feed_data)


def main():
    synthesiser = SynthesiserRestStomp()

    # Create Synthesiser Twin with a Feed
    synthesiser.create_new_twin(
        twin_key_name="TwinSynthesiser",
        properties=[
            {
                "key": PROPERTY_KEY_LABEL,
                "langLiteralValue": {
                    "value": "Average Temperature Twin",
                    "lang": "en",
                },
            },
            {
                "key": PROPERTY_KEY_COMMENT,
                "langLiteralValue": {
                    "value": "A Twin that receives temperature data, compute the average and shares it",
                    "lang": "en",
                },
            },
        ],
        feeds=[
            {
                "id": "avg_temperature",
                "storeLast": True,
                "properties": [
                    {
                        "key": PROPERTY_KEY_LABEL,
                        "langLiteralValue": {
                            "value": "Average Temperature",
                            "lang": "en",
                        },
                    },
                    {
                        "key": PROPERTY_KEY_COMMENT,
                        "langLiteralValue": {
                            "value": "Average Temperature of a home",
                            "lang": "en",
                        },
                    },
                ],
                "values": [
                    {
                        "comment": "Temperature in degrees Celsius",
                        "dataType": "decimal",
                        "label": "average",
                        "unit": UNIT_DEGREE_CELSIUS,
                    }
                ],
            },
        ],
    )

    # Search for Publisher Twins based on a specific Twin Property
    logging.info("Searching for Publisher Twins...")
    twins_found = synthesiser.search_publisher_twins(
        properties=[
            {
                "key": PROPERTY_KEY_CREATED_BY,
                "stringLiteralValue": {"value": "Replace with your Name"},
            }
        ]
    )

    # For every Twin found subscribe to all its Feeds
    synthesiser.follow_feeds(twins_found=twins_found)

    logging.info("Waiting for incoming data...")
    try:
        while True:
            sleep(10)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
