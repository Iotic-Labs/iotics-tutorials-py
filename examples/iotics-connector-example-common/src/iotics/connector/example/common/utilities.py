import logging
import sys
from threading import Lock
from time import sleep, time

import grpc
import requests
from constants import (
    ERROR_RETRY_SLEEP_TIME,
    INDEX_JSON_PATH,
    TOKEN_REFRESH_PERIOD_PERCENT,
)
from identity import Identity
from iotics.lib.grpc.iotics_api import IoticsApi

logging.basicConfig(
    level=logging.getLevelName("INFO"),
    format="[%(asctime)s] %(levelname)s %(funcName)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)

log = logging.getLogger(__name__)


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


def auto_refresh_token(
    refresh_token_lock: Lock, identity: Identity, iotics_api: IoticsApi
):
    token_period: int = int(identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT)

    while True:
        time_to_refresh: int = token_period - (time() - identity.token_last_updated)
        sleep(time_to_refresh)
        with refresh_token_lock:
            identity.refresh_token()
            iotics_api.update_channel()


def is_token_expired(exception, operation: str) -> bool:
    """Control the exception raised to check whether it is related to the token being expired.

    Args:
        exception (Exception): the exception raised.
        operation (str): the operation which raised the exception.

    Returns:
        bool: True if the exception was caused by the token expired. False otherwise
    """

    if exception.code() != grpc.StatusCode.UNAUTHENTICATED:
        log.error(
            "Un unhandled gRPC exception is raised in '%s': %s",
            operation,
            exception,
        )
        return False

    sleep(ERROR_RETRY_SLEEP_TIME)
    return True
