from threading import Event, Lock
from time import sleep, time
from typing import List

from helpers.constants import TOKEN_REFRESH_PERIOD_PERCENT
from helpers.identity import Identity
from helpers.rest_client import RestClient
from helpers.stomp_client import StompClient


def auto_refresh_token(
    identity: Identity,
    event: Event,
    rest_client: RestClient,
    lock: Lock,
    stomp_client_list: List[StompClient] = [],
):
    token_period = identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT

    while True:
        start_processing_time = time()

        new_token: str = identity.generate_new_token()
        with lock:
            rest_client.new_token(token=new_token)
            for stomp_client in stomp_client_list:
                stomp_client.new_token(token=new_token)

        event.set()

        sleep(max(0, token_period - (time() - start_processing_time)))
