import base64
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from helpers.constants import (
    DELETE_TWIN,
    DESCRIBE_REMOTE_TWIN,
    DESCRIBE_TWIN,
    SEND_INPUT_MESSAGE,
    SHARE_DATA,
    UPSERT_TWIN,
)
from requests import Response, request


class RestClient:
    def __init__(self, token: str, host_url: str):
        self._token: str = token
        self._host_url: str = host_url
        self._headers: dict = {}

        self._setup()

    def _setup(self):
        self._headers = {
            "accept": "application/json",
            "Iotics-ClientAppId": "rest_client",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
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
            logging.error("Payload: %s", payload)
            sys.exit(1)

        return response

    def new_token(self, token: str):
        self._headers["Authorization"] = f"Bearer {token}"

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
            method=UPSERT_TWIN.method,
            headers=self._headers,
            endpoint=UPSERT_TWIN.url.format(host=self._host_url),
            payload=payload,
        )

        logging.info("Twin %s created", twin_did)

    def describe_twin(self, twin_did: str, host_id: str = None) -> dict:
        describe_twin_endpoint = DESCRIBE_TWIN.url.format(
            host=self._host_url, twin_did=twin_did
        )

        if host_id:
            describe_twin_endpoint = DESCRIBE_REMOTE_TWIN.url.format(
                host=self._host_url, twin_did=twin_did, host_id=host_id
            )

        twin_description: dict = self._make_api_call(
            method=DESCRIBE_TWIN.method,
            headers=self._headers,
            endpoint=describe_twin_endpoint,
        )
        
        return twin_description

    def share_data(
        self, publisher_twin_did: str, host_id: str, feed_id: str, data_to_share: dict
    ):
        encoded_data: str = base64.b64encode(
            json.dumps(data_to_share).encode()
        ).decode()
        data_to_share_payload: dict = {
            "sample": {"data": encoded_data, "mime": "application/json"}
        }

        self._make_api_call(
            method=SHARE_DATA.method,
            headers=self._headers,
            endpoint=SHARE_DATA.url.format(
                host=self._host_url,
                host_id=host_id,
                twin_id=publisher_twin_did,
                feed_id=feed_id,
            ),
            payload=data_to_share_payload,
        )

        logging.info("Shared %s from Twin %s", data_to_share, publisher_twin_did)

    def send_input_message(
        self, twin_sender_did: str, twin_receiver_did: str, input_id: str, message: dict
    ):
        encoded_data: str = base64.b64encode(json.dumps(message).encode()).decode()
        message_to_send_payload: dict = {
            "message": {"data": encoded_data, "mime": "application/json"}
        }

        self._make_api_call(
            method=SEND_INPUT_MESSAGE.method,
            headers=self._headers,
            endpoint=SEND_INPUT_MESSAGE.url.format(
                host=self._host_url,
                twin_sender_id=twin_sender_did,
                twin_receiver_id=twin_receiver_did,
                input_id=input_id,
            ),
            payload=message_to_send_payload,
        )

    def search_twins(
        self,
        text: Optional[str] = None,
        location: Optional[dict] = None,
        properties: Optional[List[dict]] = None,
        scope: Optional[str] = "LOCAL",
        response_type: Optional[str] = "FULL",
        timeout: Optional[int] = 5,
    ) -> list[dict]:
        twins_list = []

        search_headers: dict = self._headers.copy()
        # Search headers require a new header "Iotics-RequestTimeout".
        # The latter is used to stop the request once the timeout is reached
        search_headers.update(
            {
                "Iotics-RequestTimeout": (
                    datetime.now(tz=timezone.utc) + timedelta(seconds=float(timeout))
                ).isoformat(),
            }
        )

        payload: dict = {"responseType": response_type, "filter": {}}

        if text:
            payload["filter"]["text"] = text
        if properties:
            payload["filter"]["properties"] = properties
        if location:
            payload["filter"]["location"] = location

        with request(
            method="POST",
            url=f"{self._host_url}/qapi/searches",
            headers=search_headers,
            stream=True,
            verify=True,
            params={"scope": scope},
            json=payload,
        ) as resp:
            resp.raise_for_status()
            # Iterates over the response data, one Host at a time
            for chunk in resp.iter_lines():
                response = json.loads(chunk)
                twins_found = []
                try:
                    twins_found = response["result"]["payload"]["twins"]
                except KeyError:
                    continue
                finally:
                    if twins_found:
                        # Append the twins found to the list of twins
                        twins_list.extend(twins_found)

        logging.info("Found %d twin(s)", len(twins_list))

        return twins_list

    def delete_twin(self, twin_did: str):
        self._make_api_call(
            method=DELETE_TWIN.method,
            headers=self._headers,
            endpoint=DELETE_TWIN.url.format(host=self._host_url, twin_did=twin_did),
        )

        logging.info("Twin %s deleted", twin_did)
