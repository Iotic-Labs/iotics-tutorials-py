import logging
import sys
from time import sleep, time

import requests
from constants import INDEX_JSON_PATH, TOKEN_REFRESH_PERIOD_PERCENT
from identity import Identity
from iotics.lib.grpc.iotics_api import IoticsApi as IOTICSviagRPC


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


def auto_refresh_token(identity: Identity, iotics_api: IOTICSviagRPC):
    token_period: int = int(identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT)

    while True:
        time_to_refresh: int = token_period - (time() - identity.token_last_updated)
        try:
            sleep(time_to_refresh)
            identity.refresh_token()
            iotics_api.update_channel()
        except KeyboardInterrupt:
            logging.debug("Keyboard Interrupt. Exiting Thread")
            break
