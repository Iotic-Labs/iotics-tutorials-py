import logging
import sys
from time import time
from typing import Optional

import requests
from helpers.constants import INDEX_JSON_PATH, TOKEN_REFRESH_PERIOD_PERCENT
from helpers.identity import Identity
from helpers.rest_client import RestClient
from helpers.stomp_client import StompClient
from iotics.lib.grpc.iotics_api import IoticsApi as IOTICSviagRPC


def auto_refresh_token_grpc(identity: Identity, iotics_api: IOTICSviagRPC):
    while True:
        lasted: float = time() - identity.token_last_updated
        if lasted >= identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT:
            identity.refresh_token()
            iotics_api.update_channel()


def auto_refresh_token_rest_stomp(
    identity: Identity,
    rest_client: RestClient,
    stomp_client: Optional[StompClient] = None,
):
    while True:
        lasted: float = time() - identity.token_last_updated
        if lasted >= identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT:
            identity.refresh_token()
            new_token: str = identity.get_token()
            rest_client.new_token(token=new_token)

            if stomp_client:
                stomp_client.new_token(token=new_token)


def get_host_endpoints(host_url: str) -> dict:
    if not host_url:
        logging.error("Parameter HOST_URL not set")
        sys.exit(1)

    index_json: str = host_url + INDEX_JSON_PATH
    req_resp: dict = {}

    try:
        req_resp = requests.get(index_json).json()
    except requests.exceptions.ConnectionError:
        logging.error(
            "Can't connect to %s. Check HOST_URL is spelt correctly", index_json
        )
        sys.exit(1)

    return req_resp
