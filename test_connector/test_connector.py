import base64
import json
import logging
import sys
from threading import Event, Thread
from time import sleep

from helpers.identity import Identity
from helpers.rest_client import RestClient
from helpers.stomp_client import StompClient
from helpers.utilities import auto_refresh_token, get_host_endpoints

HOST_URL = "https://demo.dev.iotics.space"

USER_KEY_NAME = ""
USER_SEED = ""
AGENT_KEY_NAME = ""
AGENT_SEED = ""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class TestConnector:
    def __init__(self):
        self._identity: Identity = None
        self._rest_client: RestClient = None
        self._stomp_client_feed: StompClient = None
        self._twin_1_did: str = None
        self._twin_2_did: str = None
        self._feed_id: str = "feed_id"
        self._feed_label: str = "feed_label"
        self._input_id: str = "input_id"
        self._input_label: str = "input_label"

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
            token_duration=15,
        )
        self._rest_client = RestClient(host_url=HOST_URL)
        self._stomp_client_feed = StompClient(
            stomp_endpoint=endpoints["stomp"],
            callback=self._follow_feed_callback,
        )

        event = Event()
        Thread(
            target=auto_refresh_token,
            args=(
                self._identity,
                event,
                self._rest_client,
                [self._stomp_client_feed],
            ),
            daemon=True,
        ).start()
        event.wait()

    def _follow_feed_callback(self, headers, body):
        encoded_data = json.loads(body)

        try:
            received_data = encoded_data["feedData"]["data"]
        except KeyError:
            logging.error("No data")
        else:
            decoded_feed_data = json.loads(
                base64.b64decode(received_data).decode("ascii")
            )
            logging.info("Received Feed data %s", decoded_feed_data)

    def _subscribe_to_feed(self):
        subscribe_to_feed_endpoint: str = f"/qapi/twins/{self._twin_2_did}/interests/twins/{self._twin_1_did}/feeds/{self._feed_id}"
        self._stomp_client_feed.subscribe(
            topic=subscribe_to_feed_endpoint,
            subscription_id=f"{self._twin_1_did}-{self._feed_id}",
        )

    def _create_twins(self):
        # Create Twin 1 with 1 Feed and 1 Input
        twin_1_registered_identity = self._identity.create_twin_with_control_delegation(
            twin_key_name="twin_1"
        )
        self._twin_1_did = twin_1_registered_identity.did
        self._rest_client.upsert_twin(
            twin_did=self._twin_1_did,
            feeds=[
                {
                    "id": self._feed_id,
                    "values": [{"dataType": "integer", "label": self._feed_label}],
                },
            ],
            inputs=[
                {
                    "id": self._input_id,
                    "values": [{"dataType": "integer", "label": self._input_label}],
                },
            ],
        )

        # Create Twin 2
        twin_2_registered_identity = self._identity.create_twin_with_control_delegation(
            twin_key_name="twin_2"
        )
        self._twin_2_did = twin_2_registered_identity.did
        self._rest_client.upsert_twin(twin_did=self._twin_2_did)

    def _test_1(self):
        self._subscribe_to_feed()
        logging.info("--- STEP 1 ---")
        self._share_data()
        logging.info("--- STEP 3 ---")
        self._share_data(token_duration=10)
        logging.info("--- STEP 4 ---")
        self._share_data(token_duration=5)
        sleep(5)

    def clear_space(self):
        self._rest_client.delete_twin(twin_did=self._twin_1_did)
        self._rest_client.delete_twin(twin_did=self._twin_2_did)

    def _share_data(self, token_duration: int = None):
        count = 0
        if token_duration:
            self._identity.set_token_duration(duration=token_duration)

        while count < 30:
            try:
                self._rest_client.share_data(
                    publisher_twin_did=self._twin_1_did,
                    feed_id=self._feed_id,
                    data_to_share={self._feed_label: count},
                )
            except KeyboardInterrupt:
                break
            else:
                count += 1
                sleep(1)

    def run(self):
        self._create_twins()
        self._test_1()


def main():
    test_connector = TestConnector()
    test_connector.run()
    test_connector.clear_space()


if __name__ == "__main__":
    main()
