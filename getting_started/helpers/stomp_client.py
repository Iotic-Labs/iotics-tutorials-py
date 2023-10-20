"""The following STOMP Client and STOMP Listener Classes are only useful as a guidelines
and should not be used in production. For a more robust version of these Classes
please refer to the "examples" folder.
"""
import json
from typing import Callable
import uuid

import stomp
from iotic.web.stomp.client import StompWSConnection12


class StompClient:
    def __init__(self, stomp_endpoint: str, callback: Callable, token: str):
        client_app_id = uuid.uuid4().hex
        self._headers: dict = {"Iotics-ClientAppId": client_app_id}
        self._stomp_connection: StompWSConnection12 = StompWSConnection12(
            endpoint=stomp_endpoint, heartbeats=(10000, 10000), use_ssl=True
        )
        self._stomp_connection.set_listener(
            name=f"{client_app_id}_stomp_listener",
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
