import logging
import sys
from datetime import datetime
from threading import Event
from time import sleep, time
from typing import List

import requests

from helpers.constants import INDEX_JSON_PATH, TOKEN_REFRESH_PERIOD_PERCENT
from helpers.identity import Identity
from helpers.rest_client import RestClient
from helpers.stomp_client import StompClient


def auto_refresh_token(
    identity: Identity,
    event: Event,
    rest_client: RestClient,
    stomp_client_list: List[StompClient] = [],
):
    """Refreshes the JWT token for the REST and Stomp Client connections with
        IOTICS
    Args:
        identity (Identity): Identity Class
        event (Event): Thread Event to set when complete
        rest_client (RestClient): Rest Client for IOTICS
        stomp_client_list (List[StompClient], optional): Stomp Clients for
            IOTICS space. Defaults to [].
    """

    token_period = int(identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT)

    while True:
        start_processing_time = time()

        new_token: str = identity.generate_new_token()
        logging.info(
            "New token generated valid until %s",
            datetime.fromtimestamp(time() + identity.token_duration),
        )
        rest_client.new_token(token=new_token)
        for stomp_client in stomp_client_list:
            stomp_client.new_token(token=new_token)

        event.set()

        sleep(token_period - (time() - start_processing_time))


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
