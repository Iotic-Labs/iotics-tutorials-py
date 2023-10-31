import base64
import json
import logging
import os
from threading import Lock
from time import sleep
import uuid
from typing import List, Optional

import helpers.constants as constant
import requests
from requests import Response, request
from requests_ntlm2 import HttpNtlmAdapter, HttpNtlmAuth, NtlmCompatibility


class RestClient:
    def __init__(self, host_url: str, lock: Lock, proxy: bool = True):
        self._host_url: str = host_url
        self._headers: dict = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Iotics-ClientAppId": uuid.uuid4().hex,
        }
        self._request: requests.Session = None
        self._lock: Lock = lock
        if proxy:
            session = self._get_session(
                user_name=constant.USER_NAME_ACCESS,
                user_pass=constant.USER_PASS_ACCESS,
                proxy_http=constant.HTTP_PROXY,
                proxy_https=constant.HTTPS_PROXY,
            )
            self._request: requests.Session = session.request

    @staticmethod
    def _get_session(
        user_name: str,
        user_pass: str,
        proxy_http: str,
        proxy_https: str,
    ) -> requests.Session:
        """Create a Request Session to go through Proxies

        Args:
            user_name (str): Username for proxy - Windows username
            user_pass (str): Password for Proxy - Windows password
            proxy_http (str): HTTP of proxy
            proxy_https (str): HTTPS of proxy

        Returns:
            requests.Session: Request Session with mounted authorisation
                credentials in NTLM (Windows credentials)
        """
        ntlm_compatibility = NtlmCompatibility.NTLMv2_DEFAULT
        created_session = requests.Session()

        # Mount adapter for "http://"
        nltp_adapter = HttpNtlmAdapter(
            user_name, user_pass, ntlm_compatibility=ntlm_compatibility
        )
        created_session.mount("http://", nltp_adapter)

        # Mount adapter for "https://"
        nltp_adapter_https = HttpNtlmAdapter(
            user_name, user_pass, ntlm_compatibility=ntlm_compatibility
        )
        created_session.mount("https://", nltp_adapter_https)

        created_session.auth = HttpNtlmAuth(
            user_name, user_pass, ntlm_compatibility=ntlm_compatibility
        )
        created_session.proxies = {
            "http": proxy_http,
            "https": proxy_https,
        }

        created_session.verify = os.environ.get("REQUESTS_CA_BUNDLE")

        return created_session

    def _make_api_call(
        self,
        method: str,
        endpoint: str,
        headers: Optional[dict] = None,
        payload: Optional[dict] = None,
    ) -> (dict, bool):
        response: dict = None
        error_flag: bool = True
        retry_attempt: int = 0
        sleep_time = 0.25

        while retry_attempt < 3:
            with self._lock:
                try:
                    if self._request:
                        req_resp: Response = self._request(
                            method=method, url=endpoint, headers=headers, json=payload
                        )
                    else:
                        req_resp: Response = request(
                            method=method, url=endpoint, headers=headers, json=payload
                        )
                    req_resp.raise_for_status()
                    response = req_resp.json()
                except Exception as ex:
                    logging.error("Getting error %s", ex)
                    sleep_time += 0.25
                    retry_attempt += 1
                    logging.debug("Retrying rest operation")
                else:
                    error_flag = False
                    break

            sleep(sleep_time)

        return response, error_flag

    def new_token(self, token: str):
        with self._lock:
            self._headers.update({"Authorization": f"Bearer {token}"})

    def upsert_twin(
        self,
        twin_did: str,
        properties: Optional[List[dict]] = None,
        feeds: Optional[List[dict]] = None,
        inputs: Optional[List[dict]] = None,
        location: Optional[dict] = None,
    ) -> dict:
        payload: dict = {"twinId": {"id": twin_did}}

        if location:
            payload["location"] = location
        if feeds:
            payload["feeds"] = feeds
        if inputs:
            payload["inputs"] = inputs
        if properties:
            payload["properties"] = properties

        response, error_flag = self._make_api_call(
            method=constant.UPSERT_TWIN.method,
            headers=self._headers,
            endpoint=constant.UPSERT_TWIN.url.format(host=self._host_url),
            payload=payload,
        )

        if not error_flag:
            logging.info("Twin %s created", twin_did)

        return response

    def delete_twin(self, twin_did: str) -> dict:
        response, error_flag = self._make_api_call(
            method=constant.DELETE_TWIN.method,
            headers=self._headers,
            endpoint=constant.DELETE_TWIN.url.format(
                host=self._host_url, twin_id=twin_did
            ),
        )

        if not error_flag:
            logging.info("Twin %s deleted", twin_did)

        return response

    def share_data(
        self, publisher_twin_did: str, feed_id: str, data_to_share: dict
    ) -> dict:
        encoded_data: str = base64.b64encode(
            json.dumps(data_to_share).encode()
        ).decode()
        data_to_share_payload: dict = {
            "sample": {"data": encoded_data, "mime": "application/json"}
        }

        response, error_flag = self._make_api_call(
            method=constant.SHARE_DATA.method,
            headers=self._headers,
            endpoint=constant.SHARE_DATA.url.format(
                host=self._host_url, twin_id=publisher_twin_did, feed_id=feed_id
            ),
            payload=data_to_share_payload,
        )

        if not error_flag:
            logging.info("Shared Feed data %s", data_to_share)

        return response

    def send_input_message(
        self,
        sender_twin_did: str,
        receiver_twin_id: str,
        input_id: str,
        input_msg: dict,
    ) -> dict:
        encoded_data: str = base64.b64encode(json.dumps(input_msg).encode()).decode()
        message_to_send: dict = {
            "message": {"data": encoded_data, "mime": "application/json"}
        }

        response, error_flag = self._make_api_call(
            method=constant.SEND_INPUT_MESSAGE.method,
            headers=self._headers,
            endpoint=constant.SEND_INPUT_MESSAGE.url.format(
                host=self._host_url,
                twin_sender_id=sender_twin_did,
                twin_receiver_id=receiver_twin_id,
                input_id=input_id,
            ),
            payload=message_to_send,
        )

        if not error_flag:
            logging.info("Sent Input message %s", input_msg)

        return response
