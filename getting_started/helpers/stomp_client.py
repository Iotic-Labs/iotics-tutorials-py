import json
from typing import Callable

import stomp
from iotic.web.stomp.client import StompWSConnection12


class StompClient:
    def __init__(self, stomp_endpoint: str, callback: Callable, token: str):
        self._headers: dict = {
            "accept": "application/json",
            "Iotics-ClientAppId": "stomp",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        self._stomp_connection: StompWSConnection12 = StompWSConnection12(
            endpoint=stomp_endpoint, heartbeats=(10000, 10000), use_ssl=True
        )
        self._stomp_connection.set_listener(
            name="stomp_listener",
            lstnr=StompListener(callback=callback),
        )
        self._stomp_connection.connect(wait=True, passcode=token)

    def subscribe(self, topic: str, subscription_id: str):
        self._stomp_connection.subscribe(
            destination=topic, id=subscription_id, headers=self._headers
        )


class StompListener(stomp.ConnectionListener):
    def __init__(self, callback: Callable):
        self._callback: Callable = callback

    def on_error(self, headers, body):
        error_msg = json.loads(body)
        print("Received an unhandled error ", error_msg)

    def on_message(self, headers, body):
        self._callback(headers, body)

    def on_disconnected(self):
        print("STOMP Listener disconnected")
