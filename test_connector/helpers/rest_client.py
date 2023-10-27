import base64
import json
import logging
import sys
import uuid
from typing import List, Optional

from requests import Response, request

import helpers.constants as constant


class RestClient:
    def __init__(self, host_url: str):
        self._host_url: str = host_url
        self._headers: dict = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Iotics-ClientAppId": uuid.uuid4().hex,
        }

    @staticmethod
    def _make_api_call(
        method: str,
        endpoint: str,
        headers: Optional[dict] = None,
        payload: Optional[dict] = None,
    ) -> dict:
        response: dict = {}

        try:
            req_resp: Response = request(
                method=method, url=endpoint, headers=headers, json=payload
            )
            req_resp.raise_for_status()
            response = req_resp.json()
        except Exception as ex:
            logging.error("Getting error %s", ex)
            sys.exit(1)

        return response

    def new_token(self, token: str):
        self._headers.update({"Authorization": f"Bearer {token}"})

    def upsert_twin(
        self,
        twin_did: str,
        properties: Optional[List[dict]] = None,
        feeds: Optional[List[dict]] = None,
        inputs: Optional[List[dict]] = None,
        location: Optional[dict] = None,
    ):
        payload: dict = {"twinId": {"id": twin_did}}

        if location:
            payload["location"] = location
        if feeds:
            payload["feeds"] = feeds
        if inputs:
            payload["inputs"] = inputs
        if properties:
            payload["properties"] = properties

        self._make_api_call(
            method=constant.UPSERT_TWIN.method,
            headers=self._headers,
            endpoint=constant.UPSERT_TWIN.url.format(host=self._host_url),
            payload=payload,
        )

        logging.info("Twin %s created", twin_did)

    def delete_twin(self, twin_did: str):
        self._make_api_call(
            method=constant.DELETE_TWIN.method,
            headers=self._headers,
            endpoint=constant.DELETE_TWIN.url.format(
                host=self._host_url, twin_id=twin_did
            ),
        )

    def share_data(self, publisher_twin_did: str, feed_id: str, data_to_share: dict):
        encoded_data: str = base64.b64encode(
            json.dumps(data_to_share).encode()
        ).decode()
        data_to_share_payload: dict = {
            "sample": {"data": encoded_data, "mime": "application/json"}
        }

        self._make_api_call(
            method=constant.SHARE_DATA.method,
            headers=self._headers,
            endpoint=constant.SHARE_DATA.url.format(
                host=self._host_url, twin_id=publisher_twin_did, feed_id=feed_id
            ),
            payload=data_to_share_payload,
        )

        logging.info("Shared Feed data %s", data_to_share)

    def send_input_message(
        self,
        sender_twin_did: str,
        receiver_twin_host_id: str,
        receiver_twin_id: str,
        input_id: str,
        input_msg: dict,
    ):
        encoded_data: str = base64.b64encode(json.dumps(input_msg).encode()).decode()
        message_to_send: dict = {
            "message": {"data": encoded_data, "mime": "application/json"}
        }

        self._make_api_call(
            method=constant.SEND_INPUT_MESSAGE.method,
            headers=self._headers,
            endpoint=constant.SEND_INPUT_MESSAGE.url.format(
                host=self._host_url,
                host_id=receiver_twin_host_id,
                twin_sender_id=sender_twin_did,
                twin_receiver_id=receiver_twin_id,
                input_id=input_id,
            ),
            payload=message_to_send,
        )
