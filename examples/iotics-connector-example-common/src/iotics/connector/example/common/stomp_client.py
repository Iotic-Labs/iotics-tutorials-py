import json
import logging
import uuid
from time import sleep
from typing import Callable

import stomp
from iotic.web.stomp.client import StompWSConnection12

# logging.getLogger("stomp.py").setLevel(level=logging.INFO)


class StompClient:
    def __init__(self, stomp_endpoint: str, callback: Callable):
        self._stomp_endpoint: str = stomp_endpoint
        self._callback: Callable = callback
        self._token: str = None
        self._headers: dict = {}
        self._stomp_connection: StompWSConnection12 = None
        self._subscriptions: dict = {}

        self._initialise()

    def _initialise(self):
        self._client_app_id: str = uuid.uuid4().hex
        self._headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Iotics-ClientAppId": self._client_app_id,
            "Authorization": f"Bearer {self._token}",
        }

        self._stomp_connection = StompWSConnection12(
            endpoint=self._stomp_endpoint, heartbeats=(10000, 10000), use_ssl=True
        )

    def _setup(self):
        logging.debug("stomp setup...")

        try:
            self._stomp_connection.remove_listener(
                f"{self._client_app_id}_stomp_listener"
            )
        except KeyError:
            logging.debug("No listener connected (yet)")
        else:
            logging.debug("Disconnected from listener")
            self._stomp_connection.disconnect()
            sleep(0.1)

        self._stomp_connection.set_listener(
            name=f"{self._client_app_id}_stomp_listener",
            lstnr=StompListener(
                disconnect_handler=self._disconnect_listener, callback=self._callback
            ),
        )
        self._stomp_connection.connect(wait=True, passcode=self._token)

        for topic, subscription_id in self._subscriptions.items():
            self._stomp_connection.subscribe(
                destination=topic, id=subscription_id, headers=self._headers
            )

    def new_token(self, token: str):
        self._token = token
        self._setup()

    def _disconnect_listener(self):
        self._setup()

    def subscribe(self, topic: str, subscription_id: str, retry: int = 0):
        self._stomp_connection.subscribe(
            destination=topic, id=subscription_id, headers=self._headers
        )

        self._subscriptions[topic] = subscription_id

    # TODO def unsubscribe(self, subscription_id: str):


class StompListener(stomp.ConnectionListener):
    def __init__(self, disconnect_handler: Callable, callback: Callable):
        self._disconnect_handler: Callable = disconnect_handler
        self._callback: Callable = callback
        self._reconnect: bool = False

    def on_connected(self, headers, body):
        logging.debug("STOMP Listener connected")

    def on_error(self, headers, body):
        error_msg = json.loads(body)

        if error_msg["code"] == 16:  # Code = 16 -> "token expired"
            logging.error("STOMP Listener - 'on_error': %s", error_msg)
            self._reconnect = True
        else:
            logging.error("STOMP Listener - received an unhandled error: %s", error_msg)
            self._reconnect = False

    def on_message(self, headers, body):
        self._callback(headers, body)

    def on_heartbeat_timeout(self):
        self._disconnect_handler()

    def on_disconnected(self):
        if self._reconnect:
            logging.warning("STOMP Listener disconnected. Attempting reconnect in 0.5s")
            sleep(0.5)
            self._disconnect_handler()
        else:
            logging.debug("STOMP Listener disconnected")
