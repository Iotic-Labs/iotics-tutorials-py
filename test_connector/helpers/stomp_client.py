import json
import logging
import sys
from threading import Lock
import uuid
from time import sleep
from typing import Callable

import stomp
from iotic.web.stomp.client import StompWSConnection12
from stomp.exception import NotConnectedException

logging.getLogger("stomp.py").setLevel(level=logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class StompClient:
    def __init__(self, stomp_endpoint: str, callback: Callable, name: str, lock: Lock):
        self._stomp_endpoint: str = stomp_endpoint
        self._callback: Callable = callback
        self._token: str = None
        self._headers: dict = {}
        self._stomp_connection: StompWSConnection12 = None
        self._subscriptions: dict = {}
        self._sleep_time: float = None
        self._reconnection_attempt: int = None
        self._name = name
        self._lock: Lock = lock

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
            logging.debug("%s - Number of connection retries exceeded", self._name)
            sys.exit(0)

        try:
            self._stomp_connection.remove_listener(
                f"{self._client_app_id}_stomp_listener"
            )
        except KeyError:
            logging.debug("%s - No listener connected (yet)", self._name)
        else:
            logging.debug("%s - Listener removed", self._name)
            self._stomp_connection.disconnect()

        while self._stomp_connection.is_connected():
            logging.debug("%s - STOMP Client still connected", self._name)
            sleep(self._sleep_time)

        try:
            self._stomp_connection.set_listener(
                name=f"{self._client_app_id}_stomp_listener",
                lstnr=StompListener(callback=self._callback, name=self._name),
            )

            self._stomp_connection.connect(wait=True, passcode=self._token)
            logging.debug("%s - STOMP connected", self._name)

            while not self._stomp_connection.is_connected():
                logging.debug("%s - STOMP Client still NOT connected", self._name)
                sleep(self._sleep_time)

            for topic, subscription_id in self._subscriptions.items():
                self._stomp_connection.subscribe(
                    destination=topic, id=subscription_id, headers=self._headers
                )
            logging.debug("%s - STOMP subscribed", self._name)
        except Exception as ex:
            logging.debug("%s - An exception is raised: %s", self._name, ex)
            self._disconnect_handler()
        else:
            self._initialise_vars()

    def new_token(self, token: str):
        with self._lock:
            self._token = token
            self._setup()

    def _initialise_vars(self):
        self._reconnection_attempt = 0
        self._sleep_time = 0.25

    def _disconnect_handler(self):
        logging.debug("%s - Attempting reconnection...", self._name)
        self._reconnection_attempt += 1
        self._sleep_time += 1
        self._setup()

    def subscribe(self, topic: str, subscription_id: str):
        with self._lock:
            self._subscriptions.update({topic: subscription_id})
            try:
                self._stomp_connection.subscribe(
                    destination=topic, id=subscription_id, headers=self._headers
                )
            except NotConnectedException:
                logging.debug("%s - STOMP NotConnectedException is raised", self._name)
                self._disconnect_handler()

    def unsubscribe(self, topic: str, subscription_id: str):
        with self._lock:
            try:
                self._subscriptions.pop(topic)
            except KeyError:
                logging.debug("%s - No subscription called %s", self._name, topic)
            else:
                try:
                    self._stomp_connection.unsubscribe(id=subscription_id)
                except NotConnectedException:
                    logging.debug(
                        "%s - STOMP NotConnectedException is raised", self._name
                    )


class StompListener(stomp.ConnectionListener):
    def __init__(self, callback: Callable, name: str):
        self._callback: Callable = callback
        self._name = name

    def on_connected(self, headers, body):
        logging.debug("%s - STOMP Listener connected", self._name)

    def on_error(self, headers, body):
        try:
            error_msg = json.loads(body)
        except json.decoder.JSONDecodeError:
            logging.debug("%s - STOMP Listener error %s", self._name, body)
        else:
            logging.debug("%s - STOMP Listener error %s", self._name, error_msg)

    def on_message(self, headers, body):
        self._callback(headers, body)

    def on_disconnected(self):
        logging.debug("%s - STOMP Listener disconnected", self._name)
