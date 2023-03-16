import json
import logging
from typing import Callable

import stomp
from iotic.web.stomp.client import StompWSConnection12

logging.getLogger("stomp.py").setLevel(level=logging.WARNING)


class StompClient:
    def __init__(self, stomp_endpoint: str, callback: Callable, token: str):
        self._stomp_endpoint: str = stomp_endpoint
        self._callback: Callable = callback
        self._token: str = token
        self._headers: dict = {}
        self._stomp_connection: StompWSConnection12 = None
        self._subscriptions: dict = {}

        self.setup()

    def setup(self):
        self._headers = {
            "accept": "application/json",
            "Iotics-ClientAppId": "stomp",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }
        self._stomp_connection = StompWSConnection12(
            endpoint=self._stomp_endpoint, heartbeats=(10000, 10000)
        )
        self._stomp_connection.set_ssl(verify=True)
        self._stomp_connection.set_listener(
            name="stomp_listener",
            lstnr=StompListener(disconnect_handler=self.setup, callback=self._callback),
        )
        self._stomp_connection.connect(wait=True, passcode=self._token)

        for topic, subscription_id in self._subscriptions.items():
            self._stomp_connection.subscribe(
                destination=topic, id=subscription_id, headers=self._headers
            )

    def new_token(self, token: str):
        self._token = token
        self._headers["Authorization"] = f"Bearer {token}"

    def subscribe(self, topic: str, subscription_id: str):
        self._stomp_connection.subscribe(
            destination=topic, id=subscription_id, headers=self._headers
        )

        self._subscriptions[topic] = subscription_id


class StompListener(stomp.ConnectionListener):
    def __init__(self, disconnect_handler: Callable, callback: Callable):
        self._disconnect_handler: Callable = disconnect_handler
        self._callback: Callable = callback
        self._reconnection_attempt: bool = False

    def on_error(self, headers, body):
        error_msg = json.loads(body)

        if error_msg["code"] == 16:  # Code = 16 -> "token expired"
            self._reconnection_attempt = True
            self._disconnect_handler()
        else:
            self._reconnection_attempt = False
            logging.error("Received an unhandled error %s", error_msg)

    def on_message(self, headers, body):
        self._callback(headers, body)

    def on_disconnected(self):
        if not self._reconnection_attempt:
            logging.error("Disconnected")
