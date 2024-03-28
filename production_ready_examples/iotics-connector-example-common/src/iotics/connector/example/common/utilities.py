import logging
import sys
from threading import Lock
from time import sleep, time
from uuid import uuid4

import constants as constant
import grpc
import requests
from identity import Identity
from iotics.api import search_pb2
from iotics.lib.grpc.iotics_api import IoticsApi

log = logging.getLogger(__name__)


def get_host_endpoints(host_url: str) -> dict:
    """Return the endpoint info to connect to the Host.

    Args:
        host_url (str): IOTICSpace (Host) url

    Returns:
        dict: info to connect to the Host.
    """

    if not host_url:
        log.error("Parameter HOST_URL not set")
        sys.exit(1)

    index_json: str = host_url + constant.INDEX_JSON_PATH
    req_resp: dict = {}

    try:
        req_resp = requests.get(index_json, timeout=3).json()
    except requests.exceptions.ConnectionError:
        log.error("Can't connect to %s. Check HOST_URL is spelt correctly", index_json)
        sys.exit(1)

    return req_resp


def auto_refresh_token(
    refresh_token_lock: Lock, identity: Identity, iotics_api: IoticsApi
):
    """Automatically refresh then IOTICS token before it expires.

    Args:
        refresh_token_lock (Lock): used to prevent race conditions.
        identity (Identity): the instance of Identity API used to manage IOTICS Identities.
        iotics_api (IoticsApi): the instance of IOTICS gRPC API used to execute Twins operations.
    """

    token_period = int(identity.token_duration * constant.TOKEN_REFRESH_PERIOD_PERCENT)

    while True:
        time_to_refresh: int = token_period - (time() - identity.token_last_updated)
        sleep(time_to_refresh)
        with refresh_token_lock:
            identity.refresh_token()
            iotics_api.update_channel()

        log.debug("Token refreshed correctly")


def search_twins(
    search_criteria: search_pb2.SearchRequest.Payload,
    refresh_token_lock: Lock,
    iotics_api: IoticsApi,
    keep_searching: bool = True,
):
    """Wrapper of the Search Twin operation to help checking for errors
    and retrying when they occur.

    Args:
        search_criteria (Payload): search criteria for Twins in terms of
            text, properties and/or location;
        refresh_token_lock (Lock): used to prevent race conditions.
        iotics_api (IoticsApi): the instance of Identity API used to manage IOTICS Identities
        keep_searching (bool, optional): whether to keep searching if the result is an empty list.
            Defaults to True.

    Returns:
        twins_found_list: list of Twins found.
    """

    twins_found_list = []

    while True:
        for attempt in range(constant.RETRYING_ATTEMPTS):
            try:
                with refresh_token_lock:
                    for response in iotics_api.search_iter(
                        client_app_id=uuid4().hex, payload=search_criteria
                    ):
                        twins = response.payload.twins
                        twins_found_list.extend(twins)
            except grpc.RpcError as ex:
                if not expected_grpc_exception(exception=ex, operation="search_twins"):
                    break
                log.debug("Attempt #%d", attempt + 1)
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


def expected_grpc_exception(exception, operation: str) -> bool:
    """Check if the exception is what we know we can receive i.e.
    - a stream timeout which occurs if a feed has been idle for a long time (a day).
    - or auth token needs regenerating
    otherwise log the exception, the caller should retry grpc exceptions.

    Args:
        exception (Exception): the exception raised.
        operation (str): the operation which raised the exception.

    Returns:
        bool: whether the exception raised is expected (True) or not (False).
    """

    exception_code = exception.code()
    expected_exception: bool = False

    if exception_code in [
        grpc.StatusCode.UNAVAILABLE,
        grpc.StatusCode.UNAUTHENTICATED,
        grpc.StatusCode.CANCELLED,
    ]:
        log.debug("Expected exception raised in '%s': %s", operation, exception)
        expected_exception = True
    else:
        log.warning("Unexpected exception raised in '%s': %s", operation, exception)

    return expected_exception


def retry_on_exception(
    grpc_operation, function_name: str, refresh_token_lock: Lock, *args, **kwargs
):
    """Wrapper to safely retry IOTICS operations in case of failure.

    Args:
        grpc_operation: IOTICS operation to execute.
        function_name (str): name of the function to be executed.
        refresh_token_lock (Lock): used to prevent race conditions.

    Returns:
        operation_result: object returned by the function executed.
    """

    operation_result = None
    operation_successful: bool = False
    retry_sleep_time: int = 1

    for attempt in range(constant.RETRYING_ATTEMPTS):
        try:
            with refresh_token_lock:
                operation_result = grpc_operation(*args, **kwargs)
        except grpc.RpcError as ex:
            if not expected_grpc_exception(exception=ex, operation=function_name):
                log.warning("Retry attempt #%d", attempt + 1)
        else:
            operation_successful = True
            break

        sleep(retry_sleep_time)
        retry_sleep_time += 2

    if not operation_successful:
        log.exception("Reached maximum number of retries. Exiting thread..")
        sys.exit(1)

    return operation_result
