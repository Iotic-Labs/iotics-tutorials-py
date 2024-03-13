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


def search_twins(
    search_criteria,
    refresh_token_lock: Lock,
    iotics_api: IoticsApi,
    keep_searching: bool = True,
):
    twins_found_list = []

    while True:
        for _ in range(constant.RETRYING_ATTEMPTS):
            try:
                with refresh_token_lock:
                    for response in iotics_api.search_iter(
                        client_app_id=uuid4().hex, payload=search_criteria, timeout=5
                    ):
                        twins = response.payload.twins
                        twins_found_list.extend(twins)
            except grpc.RpcError as ex:
                log_unexpected_grpc_exceptions_and_sleep(
                    exception=ex, operation="search_twins"
                )
            else:
                break

        if not twins_found_list and keep_searching:
            log.info(
                "No Twins found based on the search criteria %s. Retrying in %ds",
                search_criteria,
                constant.RETRY_SLEEP_TIME,
            )
            sleep(constant.RETRY_SLEEP_TIME)
        else:
            break

    return twins_found_list


def log_unexpected_grpc_exceptions_and_sleep(exception, operation: str):
    """test if it is an exception that we know we can receive i.e.
    - a stream timeout which occurs if a feed has been idle for a long time (a day).
    - or auth token needs regenerating
    otherwise log the exception, the caller should retry grpc exceptions

    Args:
        exception (Exception): the exception raised.
        operation (str): the operation which raised the exception.

    """

    exception_code = exception.code()

    if (
        not (
            exception_code == grpc.StatusCode.UNAVAILABLE
            and exception.details() == "stream timeout"
        )
        and exception_code != grpc.StatusCode.UNAUTHENTICATED
    ):
        log.error(
            "An unexpected gRPC exception was raised in '%s': %s",
            operation,
            exception,
        )
    else:
        log.debug("Expected exception raised in '%s': %s", operation, exception)

    sleep(constant.RETRY_SLEEP_TIME)
