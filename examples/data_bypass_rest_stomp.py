import base64
import json
import logging
import sys
import threading
from time import sleep
from typing import List

from helpers.constants import (
    PROPERTY_KEY_COMMENT,
    PROPERTY_KEY_DEFINES,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_ORGANISATION,
    PROPERTY_VALUE_ORGANISATION_NAME,
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

ORGANISATIONS_ALLOWED = ["Company A"]
REQUEST_INPUT_ID = "request"
RESPONSE_INPUT_ID = "response"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class DataBypass:
    def __init__(self):
        self._identity: Identity = None
        self._rest_client: RestClient = None
        self._stomp_client_receiver: StompClient = None
        self._stomp_client_requester: StompClient = None

        self._setup()

    def _setup(self):
        endpoints = get_host_endpoints(host_url=HOST_URL)
        self._identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=USER_KEY_NAME,
            user_seed=USER_SEED,
            agent_key_name=AGENT_KEY_NAME,
            agent_seed=AGENT_SEED,
        )
        token = self._identity.get_token()
        self._rest_client = RestClient(token=token, host_url=HOST_URL)

        self._stomp_client_receiver = StompClient(
            stomp_endpoint=endpoints.get("stomp"),
            callback=self._twin_response_callback,
            token=token,
        )

        self._stomp_client_requester = StompClient(
            stomp_endpoint=endpoints.get("stomp"),
            callback=self._twin_request_callback,
            token=token,
        )

        threading.Thread(
            target=auto_refresh_token_rest_stomp,
            args=(
                self._identity,
                self._rest_client,
                self._stomp_client_receiver,
            ),
            daemon=True,
        ).start()

        threading.Thread(
            target=auto_refresh_token_rest_stomp,
            args=(
                self._identity,
                self._rest_client,
                self._stomp_client_requester,
            ),
            daemon=True,
        ).start()

    def create_new_twin(
        self, twin_key_name: str, properties: List[dict], inputs: List[dict]
    ):
        twin_identity = self._identity.create_twin_with_control_delegation(
            twin_key_name=twin_key_name
        )

        self._rest_client.upsert_twin(
            twin_did=twin_identity.did,
            properties=properties,
            inputs=inputs,
        )

        return twin_identity

    def search_twins(self, properties: List[dict] = None):
        twins_found = self._rest_client.search_twins(properties=properties)

        return twins_found

    def twin_response_wait_input(self, twin_id: str):
        self._stomp_client_receiver.subscribe(
            topic=f"/qapi/twins/{twin_id}/inputs/{REQUEST_INPUT_ID}",
            subscription_id=f"{twin_id}-{REQUEST_INPUT_ID}",
        )

    def twin_request_wait_input(self, twin_id: str):
        self._stomp_client_requester.subscribe(
            topic=f"/qapi/twins/{twin_id}/inputs/{RESPONSE_INPUT_ID}",
            subscription_id=f"{twin_id}-{RESPONSE_INPUT_ID}",
        )

    def send_db_request(self, twin_sender_id: str, twin_receiver_id: str):
        request = {"twin_id": twin_sender_id}

        self._rest_client.send_input_message(
            twin_sender_did=twin_sender_id,
            twin_receiver_did=twin_receiver_id,
            input_id=REQUEST_INPUT_ID,
            message=request,
        )

    def cleanup(self, twins_list: List):
        for twin in twins_list:
            self._rest_client.delete_twin(twin_did=twin.did)

    def _process_request(self, twin_request_id: str, twin_response_id: str):
        logging.info("Describing Twin %s...", twin_request_id)
        twin_description = self._rest_client.describe_twin(twin_did=twin_request_id)
        twin_properties: List[dict] = twin_description["result"]["properties"]
        for property in twin_properties:
            if property["key"] == PROPERTY_VALUE_ORGANISATION_NAME:
                organisation = property["stringLiteralValue"]["value"]
                break

        if organisation in ORGANISATIONS_ALLOWED:
            self._rest_client.send_input_message(
                twin_sender_did=twin_response_id,
                twin_receiver_did=twin_request_id,
                input_id=RESPONSE_INPUT_ID,
                message={"passcode": "1234567890"},
            )
        else:
            logging.info("Twin %s not allowed", twin_request_id)

    def _twin_response_callback(self, headers, body):
        encoded_data = json.loads(body)

        try:
            encoded_input_data: dict = encoded_data["message"]["data"]
        except KeyError:
            logging.error("No data")
        else:
            decoded_input_data = json.loads(
                base64.b64decode(encoded_input_data).decode("ascii")
            )
            twin_response_id = encoded_data["inputId"]["twinId"]
            twin_request_id = decoded_input_data["twin_id"]
            logging.info("Received input message %s", decoded_input_data)
            self._process_request(
                twin_request_id=twin_request_id, twin_response_id=twin_response_id
            )

    def _twin_request_callback(self, headers, body):
        encoded_data = json.loads(body)

        try:
            data = encoded_data["message"]["data"]
        except KeyError:
            logging.error("No data")
        else:
            decoded_input_data = json.loads(base64.b64decode(data).decode("ascii"))
            logging.info("Received input message %s", decoded_input_data)
            # ACCESS THE DB


def main():
    data_bypass = DataBypass()

    twins_list: List[str] = []

    # Create Twin Response
    twin_response_identity = data_bypass.create_new_twin(
        twin_key_name="twin_response",
        properties=[
            {
                "key": PROPERTY_KEY_LABEL,
                "langLiteralValue": {"value": "Twin Response", "lang": "en"},
            },
            {
                "key": PROPERTY_KEY_COMMENT,
                "langLiteralValue": {
                    "value": "A Twin that receives Input requests and processes responses",
                    "lang": "en",
                },
            },
        ],
        inputs=[
            {
                "id": REQUEST_INPUT_ID,
                "values": [{"dataType": "string", "label": "twin_id"}],
            },
        ],
    )

    twins_list.append(twin_response_identity)
    data_bypass.twin_response_wait_input(twin_id=twin_response_identity.did)

    # Create Twin Request 1
    twin_request_1_identity = data_bypass.create_new_twin(
        twin_key_name="twin_request_1",
        properties=[
            {
                "key": PROPERTY_KEY_LABEL,
                "langLiteralValue": {"value": "Twin Request 1", "lang": "en"},
            },
            {
                "key": PROPERTY_KEY_COMMENT,
                "langLiteralValue": {
                    "value": "A Twin that sends Input requests and receives responses",
                    "lang": "en",
                },
            },
            {
                "key": PROPERTY_KEY_DEFINES,
                "uriValue": {"value": PROPERTY_KEY_ORGANISATION},
            },
            {
                "key": PROPERTY_VALUE_ORGANISATION_NAME,
                "stringLiteralValue": {"value": "Company A"},
            },
        ],
        inputs=[
            {
                "id": RESPONSE_INPUT_ID,
                "values": [{"dataType": "string", "label": "passcode"}],
            },
        ],
    )

    twins_list.append(twin_request_1_identity)
    data_bypass.twin_request_wait_input(twin_id=twin_request_1_identity.did)

    # Create Twin Request 2
    twin_request_2_identity = data_bypass.create_new_twin(
        twin_key_name="twin_request_2",
        properties=[
            {
                "key": PROPERTY_KEY_LABEL,
                "langLiteralValue": {"value": "Twin Request 2", "lang": "en"},
            },
            {
                "key": PROPERTY_KEY_COMMENT,
                "langLiteralValue": {
                    "value": "A Twin that sends Input requests and receives responses",
                    "lang": "en",
                },
            },
            {
                "key": PROPERTY_KEY_DEFINES,
                "uriValue": {"value": PROPERTY_KEY_ORGANISATION},
            },
            {
                "key": PROPERTY_VALUE_ORGANISATION_NAME,
                "stringLiteralValue": {"value": "Company B"},
            },
        ],
        inputs=[
            {
                "id": RESPONSE_INPUT_ID,
                "values": [{"dataType": "string", "label": "passcode"}],
            },
        ],
    )

    twins_list.append(twin_request_2_identity)
    data_bypass.twin_request_wait_input(twin_id=twin_request_2_identity.did)

    # Search for Twin Response
    logging.info("Searching for Twin Response...")
    twins_found: List[dict] = data_bypass.search_twins(
        properties=[
            {
                "key": PROPERTY_KEY_LABEL,
                "langLiteralValue": {"value": "Twin Response", "lang": "en"},
            }
        ]
    )
    twin_receiver: dict = next(iter(twins_found))
    twin_receiver_id: str = twin_receiver["twinId"]["id"]

    # Twin Request 1 sends a DB request to Twin Response
    logging.info("Sending DB request message from Twin Request 1...")
    data_bypass.send_db_request(
        twin_sender_id=twin_request_1_identity.did, twin_receiver_id=twin_receiver_id
    )

    # Twin Request 2 sends a DB request to Twin Response
    logging.info("Sending DB request message from Twin Request 2...")
    data_bypass.send_db_request(
        twin_sender_id=twin_request_2_identity.did, twin_receiver_id=twin_receiver_id
    )

    try:
        logging.info("Press Ctrl+C to exit...")
        while True:
            sleep(10)
    except KeyboardInterrupt:
        logging.info("Cleaning up environment...")
        data_bypass.cleanup(twins_list=twins_list)


if __name__ == "__main__":
    main()
