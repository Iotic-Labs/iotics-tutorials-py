import logging
import sys
from threading import Lock
from time import sleep, time
from uuid import uuid4

import constants as constant
import grpc
import requests
from identity import Identity
from iotics.lib.grpc.iotics_api import IoticsApi

logging.basicConfig(
    level=logging.getLevelName("INFO"),
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)

log = logging.getLogger(__name__)


def get_host_endpoints(host_url: str) -> dict:
    if not host_url:
        logging.error("Parameter HOST_URL not set")
        sys.exit(1)

    index_json: str = host_url + constant.INDEX_JSON_PATH
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
    token_period: int = int(
        identity.token_duration * constant.TOKEN_REFRESH_PERIOD_PERCENT
    )

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

    sleep(constant.RETRY_SLEEP_TIME)
    return True


def search_twins(
    search_criteria,
    refresh_token_lock: Lock,
    iotics_api: IoticsApi,
    keep_searching: bool = True,
):
    twins_found_list = []

    while True:
        try:
            with refresh_token_lock:
                for response in iotics_api.search_iter(
                    client_app_id=uuid4().hex, payload=search_criteria, timeout=5
                ):
                    twins = response.payload.twins
                    twins_found_list.extend(twins)
        except grpc.RpcError as ex:
            if not is_token_expired(exception=ex, operation="search_iter"):
                log.exception(
                    "Un unhandled exception is raised in 'search_twins'.",
                    exc_info=True,
                )
                sys.exit(1)

        if not twins_found_list and keep_searching:
            log.debug(
                "No Twins found based on the search criteria %s. Retrying in %ds",
                search_criteria,
                constant.RETRY_SLEEP_TIME,
            )
            sleep(constant.RETRY_SLEEP_TIME)
        else:
            log.debug(
                "Found %d Twins based on the search criteria", len(twins_found_list)
            )
            break

    return twins_found_list
