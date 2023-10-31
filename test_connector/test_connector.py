import base64
import json
import logging
import sys
from threading import Event, Lock, Thread
from time import sleep, time

import helpers.constants as constant
from helpers.identity import Identity
from helpers.rest_client import RestClient
from helpers.stomp_client import StompClient
from helpers.utilities import auto_refresh_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class TestConnector:
    def __init__(self):
        self._identity: Identity = None
        self._rest_client: RestClient = None
        self._stomp_client_feed: StompClient = None
        self._stomp_client_input: StompClient = None
        self._lock: Lock = None
        self._twin_1_did: str = None
        self._twin_2_did: str = None

        self._setup()

    def _setup(self):
        self._identity = Identity(
            resolver_url=constant.RESOLVER_URL,
            user_key_name=constant.USER_KEY_NAME,
            user_seed=constant.USER_SEED,
            agent_key_name=constant.AGENT_KEY_NAME,
            agent_seed=constant.AGENT_SEED,
            token_duration=3,
        )
        self._lock = Lock()
        self._rest_client = RestClient(
            host_url=constant.HOST_URL, lock=self._lock, proxy=False
        )
        self._stomp_client_feed = StompClient(
            stomp_endpoint=constant.STOMP_URL,
            callback=self._follow_feed_callback,
            name="STOMP Client Feed",
            lock=self._lock,
        )
        self._stomp_client_input = StompClient(
            stomp_endpoint=constant.STOMP_URL,
            callback=self._receive_input_callback,
            name="STOMP Client Input",
            lock=self._lock,
        )

        event = Event()
        Thread(
            target=auto_refresh_token,
            args=(
                self._identity,
                event,
                self._rest_client,
                [self._stomp_client_feed, self._stomp_client_input],
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

    def _receive_input_callback(self, headers, body):
        encoded_data = json.loads(body)

        try:
            received_data = encoded_data["message"]["data"]
        except KeyError:
            logging.error("No data")
        else:
            decoded_input_data = json.loads(
                base64.b64decode(received_data).decode("ascii")
            )
            logging.info("Received Input message %s", decoded_input_data)

    def _subscribe_to_feed(self):
        subscribe_to_feed_endpoint: str = f"/qapi/twins/{self._twin_2_did}/interests/twins/{self._twin_1_did}/feeds/{constant.FEED_ID}"

        self._stomp_client_feed.subscribe(
            topic=subscribe_to_feed_endpoint,
            subscription_id=f"{self._twin_1_did}-{constant.FEED_ID}",
        )

    def _subscribe_to_input(self):
        subscribe_to_input_endpoint: str = (
            f"/qapi/twins/{self._twin_1_did}/inputs/{constant.INPUT_ID}"
        )

        self._stomp_client_input.subscribe(
            topic=subscribe_to_input_endpoint,
            subscription_id=f"{self._twin_1_did}-{constant.INPUT_ID}",
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
                    "id": constant.FEED_ID,
                    "values": [{"dataType": "integer", "label": constant.FEED_LABEL}],
                },
            ],
            inputs=[
                {
                    "id": constant.INPUT_ID,
                    "values": [{"dataType": "integer", "label": constant.INPUT_LABEL}],
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
        self._share_data()
        logging.info("--- END OF TEST 1 ---")

    def _test_2(self):
        self._subscribe_to_input()
        self._send_input_msg()
        logging.info("--- END OF TEST 2 ---")

    def clear_space(self):
        subscribe_to_feed_endpoint: str = f"/qapi/twins/{self._twin_2_did}/interests/twins/{self._twin_1_did}/feeds/{constant.FEED_ID}"
        self._stomp_client_feed.unsubscribe(
            topic=subscribe_to_feed_endpoint,
            subscription_id=f"{self._twin_1_did}-{constant.FEED_ID}",
        )

        subscribe_to_input_endpoint: str = (
            f"/qapi/twins/{self._twin_1_did}/inputs/{constant.INPUT_ID}"
        )
        self._stomp_client_input.unsubscribe(
            topic=subscribe_to_input_endpoint,
            subscription_id=f"{self._twin_1_did}-{constant.INPUT_ID}",
        )

        self._rest_client.delete_twin(twin_did=self._twin_1_did)
        self._rest_client.delete_twin(twin_did=self._twin_2_did)

        logging.info("Twins deleted")

    def _share_data(self):
        count = 0

        while count < 10:
            try:
                self._rest_client.share_data(
                    publisher_twin_did=self._twin_1_did,
                    feed_id=constant.FEED_ID,
                    data_to_share={constant.FEED_LABEL: count},
                )

                count += 1
                sleep(1)
            except KeyboardInterrupt:
                break

    def _send_input_msg(self):
        count = 0

        while count < 10:
            try:
                self._rest_client.send_input_message(
                    sender_twin_did=self._twin_2_did,
                    receiver_twin_id=self._twin_1_did,
                    input_id=constant.INPUT_ID,
                    input_msg={constant.INPUT_LABEL: count},
                )
                count += 1
                sleep(1)
            except KeyboardInterrupt:
                break

    def run(self):
        self._create_twins()
        self._test_1()
        self._test_2()


def main():
    test_connector = TestConnector()
    start_time = time()
    test_connector.run()
    test_connector.clear_space()
    logging.info("Elapsed time: %s seconds", round(time() - start_time, 2))


if __name__ == "__main__":
    main()
