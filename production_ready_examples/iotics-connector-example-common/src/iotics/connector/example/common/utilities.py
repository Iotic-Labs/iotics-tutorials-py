import asyncio
import logging
import sys
from uuid import uuid4

import aiohttp
import constants as constant
import grpc
from iotics.api import search_pb2
from iotics.lib.grpc.iotics_api import IoticsApi

log = logging.getLogger(__name__)


@staticmethod
def check_global_var(var, var_name: str):
    if not var:
        logging.error("Parameter %s not set", var_name)
        sys.exit(1)


async def get_host_endpoints(host_url: str) -> dict:
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

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=3)
        ) as session:
            async with session.get(index_json) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.error(
                        "Can't connect to %s. Check HOST_URL is spelt correctly",
                        index_json,
                    )
                    sys.exit(1)
    except asyncio.TimeoutError:
        log.error(f"Timeout connecting to {index_json}")
        sys.exit(1)
    except aiohttp.ClientError as e:
        log.error(f"Error connecting to {index_json}: {e}")
        sys.exit(1)


async def search_twins(
    search_criteria: search_pb2.SearchRequest.Payload,
    refresh_token_lock: asyncio.Lock,
    iotics_api: IoticsApi,
    keep_searching: bool = True,
    timeout: int = 3,
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
                async with refresh_token_lock:
                    for response in iotics_api.search_iter(
                        client_app_id=uuid4().hex,
                        payload=search_criteria,
                        timeout=timeout,
                    ):
                        twins = response.payload.twins
                        twins_found_list.extend(twins)
            except grpc.RpcError as ex:
                if not await expected_grpc_exception(
                    exception=ex, operation="search_twins"
                ):
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
            await asyncio.sleep(constant.RETRY_SLEEP_TIME)
        else:
            break

    return twins_found_list


async def expected_grpc_exception(exception, operation: str) -> bool:
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
        grpc.StatusCode.DEADLINE_EXCEEDED,
    ]:
        expected_exception = True
    else:
        log.warning("Unexpected exception raised in '%s': %s", operation, exception)

    await asyncio.sleep(5)

    return expected_exception


async def retry_on_exception(
    grpc_operation,
    function_name: str,
    refresh_token_lock: asyncio.Lock,
    *args,
    **kwargs,
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
            async with refresh_token_lock:
                operation_result = grpc_operation(*args, **kwargs)
        except grpc.RpcError as ex:
            if not await expected_grpc_exception(exception=ex, operation=function_name):
                log.warning("Retry attempt #%d", attempt + 1)
        else:
            operation_successful = True
            break

        await asyncio.sleep(retry_sleep_time)
        retry_sleep_time += 2

    if not operation_successful:
        log.exception("Reached maximum number of retries. Exiting thread..")
        sys.exit(1)

    return operation_result
