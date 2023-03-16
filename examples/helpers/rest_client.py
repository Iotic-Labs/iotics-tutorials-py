import base64
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from helpers.constants import GET_HOST_ID, SHARE_DATA, UPSERT_TWIN
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
            sys.exit(1)

        return response

    def new_token(self, token: str):
        self._headers["Authorization"] = f"Bearer {token}"

    def get_host_id(self):
        host_id_resp: dict = self._make_api_call(
            method=GET_HOST_ID.method,
            headers=self._headers,
            endpoint=GET_HOST_ID.url.format(host=self._host_url),
        )

        return host_id_resp.get("hostId")

    def upsert_twin(
        self,
        twin_did: str,
        host_id: str,
        properties: Optional[List[dict]] = None,
        feeds: Optional[List[dict]] = None,
        inputs: Optional[List[dict]] = None,
        location: Optional[dict] = None,
    ):
        payload: dict = {"twinId": {"hostId": host_id, "id": twin_did}}

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

        logging.info("Twin %s upserted", twin_did)

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
