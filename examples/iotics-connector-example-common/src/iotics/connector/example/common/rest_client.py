import base64
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid
import helpers.constants as constant
from requests import Response, request


class RestClient:
    def __init__(self, token: str, host_url: str):
        self._token: str = token
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
        host_id: str,
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

        logging.info("Twin %s upserted", twin_did)

    def update_twin(
        self,
        twin_did: str,
        props_to_add: List[dict] = None,
        props_to_del: List[str] = None,
        location: dict = None,
        delete_all_properties: bool = False,
    ):
        payload = {"properties": {}}

        if location:
            payload["location"] = {"location": location}
        if props_to_add:
            payload["properties"]["added"] = props_to_add
        if props_to_del:
            payload["properties"]["deletedByKey"] = props_to_del
        if delete_all_properties:
            payload["properties"]["clearedAll"] = True

        self._make_api_call(
            method=constant.UPDATE_TWIN.method,
            headers=self._headers,
            endpoint=constant.UPDATE_TWIN.url.format(
                host=self._host_url, twin_id=twin_did
            ),
            payload=payload,
        )

        logging.info("Twin %s updated", twin_did)

    def delete_twin(self, twin_did: str):
        self._make_api_call(
            method=constant.DELETE_TWIN.method,
            headers=self._headers,
            endpoint=constant.DELETE_TWIN.url.format(
                host=self._host_url, twin_id=twin_did
            ),
        )

        logging.info("Twin %s deleted", twin_did)

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

        logging.info("Shared data %s from Twin %s", data_to_share, publisher_twin_did)

    def send_input_message(
        self,
        sender_twin_did: str,
        receiver_twin_id: str,
        input_id: str,
        input_msg: dict,
        receiver_twin_host_id: str = None,
    ):
        encoded_data: str = base64.b64encode(json.dumps(input_msg).encode()).decode()
        message_to_send: dict = {
            "message": {"data": encoded_data, "mime": "application/json"}
        }

        if receiver_twin_host_id:
            self._make_api_call(
                method=constant.SEND_INPUT_MESSAGE_REMOTE.method,
                headers=self._headers,
                endpoint=constant.SEND_INPUT_MESSAGE_REMOTE.url.format(
                    host=self._host_url,
                    host_id=receiver_twin_host_id,
                    twin_sender_id=sender_twin_did,
                    receiver_twin_host_id=receiver_twin_host_id,
                    twin_receiver_id=receiver_twin_id,
                    input_id=input_id,
                ),
                payload=message_to_send,
            )
        else:
            self._make_api_call(
                method=constant.SEND_INPUT_MESSAGE_LOCAL.method,
                headers=self._headers,
                endpoint=constant.SEND_INPUT_MESSAGE_LOCAL.url.format(
                    host=self._host_url,
                    twin_sender_id=sender_twin_did,
                    twin_receiver_id=receiver_twin_id,
                    input_id=input_id,
                ),
                payload=message_to_send,
            )

        logging.info(
            "Sent input msg %s from Twin %s to Twin",
            input_msg,
            sender_twin_did,
            receiver_twin_id,
        )

    def describe_twin(self, twin_did: str, host_id: str = None) -> dict:
        if host_id:
            feed_description = self._make_api_call(
                method=constant.DESCRIBE_TWIN_REMOTE.method,
                headers=self._headers,
                endpoint=constant.DESCRIBE_TWIN_REMOTE.url.format(
                    host=self._host_url,
                    host_id=host_id,
                    twin_id=twin_did,
                ),
            )
        else:
            feed_description = self._make_api_call(
                method=constant.DESCRIBE_TWIN_LOCAL.method,
                headers=self._headers,
                endpoint=constant.DESCRIBE_TWIN_LOCAL.url.format(
                    host=self._host_url,
                    host_id=host_id,
                    twin_id=twin_did,
                ),
            )

        return feed_description

    def describe_feed(self, twin_did: str, feed_id: str, host_id: str = None) -> dict:
        if host_id:
            feed_description = self._make_api_call(
                method=constant.DESCRIBE_FEED_REMOTE.method,
                headers=self._headers,
                endpoint=constant.DESCRIBE_FEED_REMOTE.url.format(
                    host=self._host_url,
                    host_id=host_id,
                    twin_id=twin_did,
                    feed_id=feed_id,
                ),
            )
        else:
            feed_description = self._make_api_call(
                method=constant.DESCRIBE_FEED_LOCAL.method,
                headers=self._headers,
                endpoint=constant.DESCRIBE_FEED_LOCAL.url.format(
                    host=self._host_url, twin_id=twin_did, feed_id=feed_id
                ),
            )

        return feed_description

    def describe_input(self, twin_did: str, input_id: str, host_id: str = None):
        if host_id:
            feed_description = self._make_api_call(
                method=constant.DESCRIBE_INPUT_REMOTE.method,
                headers=self._headers,
                endpoint=constant.DESCRIBE_INPUT_REMOTE.url.format(
                    host=self._host_url,
                    host_id=host_id,
                    twin_id=twin_did,
                    input_id=input_id,
                ),
            )
        else:
            feed_description = self._make_api_call(
                method=constant.DESCRIBE_INPUT_LOCAL.method,
                headers=self._headers,
                endpoint=constant.DESCRIBE_INPUT_LOCAL.url.format(
                    host=self._host_url, twin_id=twin_did, input_id=input_id
                ),
            )

        return feed_description

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
        search_headers.update(
            {
                "Iotics-RequestTimeout": (
                    datetime.now(tz=timezone.utc) + timedelta(seconds=float(timeout))
                ).isoformat(),
                "Iotics-ClientAppId": uuid.uuid4().hex,
            }
        )

        payload: dict = {"responseType": response_type, "filter": {}}

        if text:
            payload["filter"]["text"] = text
        if properties:
            payload["filter"]["properties"] = properties
        if location:
            payload["filter"]["location"] = location

        with self._request(
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

        logging.debug("Found %d twin(s)", len(twins_list))

        return twins_list
