import logging
from threading import Event, Lock
from time import sleep, time
from typing import Callable, List

from helpers.constants import TOKEN_REFRESH_PERIOD_PERCENT
from helpers.identity import Identity
from helpers.rest_client import RestClient
from helpers.stomp_client import StompClient


def auto_refresh_token(
    identity: Identity,
    event: Event,
    rest_client: RestClient,
    stomp_client_list: List[StompClient] = [],
):
    token_period = identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT

    while True:
        start_processing_time = time()

        new_token: str = identity.generate_new_token()
        rest_client.new_token(token=new_token)
        for stomp_client in stomp_client_list:
            stomp_client.new_token(token=new_token)

        event.set()

        sleep(max(0, token_period - (time() - start_processing_time)))


def make_rest_operation(lock: Lock, api_operation: Callable):
    retry_attempt: int = 0
    error_flag: bool = False
    sleep_time = 0.25

    while retry_attempt < 3:
        with lock:
            error_flag, payload = api_operation

        if not error_flag:
            break

        sleep(sleep_time)
        sleep_time += 0.25
        retry_attempt += 1
        logging.debug("Retrying rest operation")

    return payload
