import json
import logging
import sys
import uuid
from time import sleep
from typing import Callable

import stomp
from iotic.web.stomp.client import StompConnectionTimeout, StompWSConnection12

logging.getLogger("stomp.py").setLevel(level=logging.WARNING)


class StompClient:
    def __init__(self, stomp_endpoint: str, callback: Callable):
        self._stomp_endpoint: str = stomp_endpoint
        self._callback: Callable = callback
        self._token: str = None
        self._headers: dict = {}
        self._stomp_connection: StompWSConnection12 = None
        self._subscriptions: dict = {}
        self._sleep_time: float = None
        self._reconnection_attempt: int = None

        self._initialise()

    def _initialise(self):
        self._client_app_id: str = uuid.uuid4().hex
        self._headers = {"Iotics-ClientAppId": self._client_app_id}
        self._stomp_connection = StompWSConnection12(
            endpoint=self._stomp_endpoint, heartbeats=(10000, 10000), use_ssl=True
        )
        self._initialise_vars()

    def _setup(self):
        if self._reconnection_attempt > 3:
            logging.error("Number of connection retries exceeded")
            sys.exit(0)

        try:
            self._stomp_connection.remove_listener(
                f"{self._client_app_id}_stomp_listener"
            )
        except KeyError:
            logging.info("No listener connected (yet)")
        else:
            logging.info("Disconnected from listener")
            self._stomp_connection.disconnect()
            sleep(self._sleep_time)

        self._stomp_connection.set_listener(
            name=f"{self._client_app_id}_stomp_listener",
            lstnr=StompListener(
                callback=self._callback, disconnect_handler=self._disconnect_handler
            ),
        )

        try:
            self._stomp_connection.connect(wait=True, passcode=self._token)
        except (stomp.exception.NotConnectedException, StompConnectionTimeout) as ex:
            logging.exception(
                "An exception is raised in 'stomp_connection.connect': %s", ex
            )
            self._disconnect_handler()
        else:
            self._initialise_vars()

        for topic, subscription_id in self._subscriptions.items():
            self._stomp_connection.subscribe(
                destination=topic, id=subscription_id, headers=self._headers
            )

    def new_token(self, token: str):
        self._token = token
        self._setup()

    def _initialise_vars(self):
        self._reconnection_attempt = 0
        self._sleep_time = 0.25

    def _disconnect_handler(self):
        logging.warning("Attempting reconnection...")
        self._reconnection_attempt += 1
        self._sleep_time += 0.25
        self._setup()

    def subscribe(self, topic: str, subscription_id: str):
        self._stomp_connection.subscribe(
            destination=topic, id=subscription_id, headers=self._headers
        )

        self._subscriptions.update({topic: subscription_id})


class StompListener(stomp.ConnectionListener):
    def __init__(self, callback: Callable, disconnect_handler: Callable):
        self._callback: Callable = callback
        self._disconnect_handler: Callable = disconnect_handler

    def on_connected(self, headers, body):
        logging.debug("STOMP Listener connected")

    def on_error(self, headers, body):
        error_msg = json.loads(body)
        logging.error("STOMP Listener error %s", error_msg)
        self._disconnect_handler()

    def on_message(self, headers, body):
        self._callback(headers, body)

    def on_disconnected(self):
        logging.debug("STOMP Listener disconnected")
