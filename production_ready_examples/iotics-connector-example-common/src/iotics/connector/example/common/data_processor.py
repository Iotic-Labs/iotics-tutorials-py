import json
import logging
from datetime import datetime
from queue import Empty, Queue
from typing import List, Tuple
import random
import constants as constant

log = logging.getLogger(__name__)


class DataProcessor:
    """Object simulating a data processor."""

    def __init__(self):
        """Constructor of the DataProcessor Class.
        It initialises a DBManager object if a DB needs to be used.

        Args:
            use_db (bool, optional): Whether or not a DB needs
                to be used for the demo. Defaults to False.
        """

        self._db_writer = None
        self._db_reader = None

    def initialise_db_writer(self, db_name: str, db_username: str, db_password: str):
        from db_writer import DBWriter

        self._db_writer = DBWriter(
            db_name=db_name, db_username=db_username, db_password=db_password
        )

    def initialise_db_reader(self, db_name: str, db_username: str, db_password: str):
        from db_reader import DBReader

        self._db_reader = DBReader(
            db_name=db_name, db_username=db_username, db_password=db_password
        )

    @staticmethod
    def feed_data_unpack(feed_data):
        received_data: dict = json.loads(feed_data.payload.feedData.data)
        occurred_at_unix_time = feed_data.payload.feedData.occurredAt.seconds
        occurred_at_timestamp = str(datetime.fromtimestamp(occurred_at_unix_time))

        return received_data, occurred_at_timestamp

    @staticmethod
    def input_data_unpack(input_message):
        received_data: dict = json.loads(input_message.payload.message.data)
        occurred_at_unix_time = input_message.payload.message.occurredAt.seconds
        occurred_at_timestamp = str(datetime.fromtimestamp(occurred_at_unix_time))

        return received_data, occurred_at_timestamp

    def print_feed_data_on_screen(
        self, publisher_twin_did: str, publisher_feed_id: str, feed_data
    ):
        """Print on screen the Feed data received.

        Args:
            publisher_twin_did (str): the Twin DID publishing data.
            publisher_feed_id (str): the Feed ID from which the data is published.
            feed_data: Feed data received.
        """

        received_data, occurred_at_timestamp = self.feed_data_unpack(feed_data)

        log.info(
            "Received data %s published by Twin DID %s via Feed %s at %s",
            received_data,
            publisher_twin_did,
            publisher_feed_id,
            occurred_at_timestamp,
        )

    def print_input_message_on_screen(
        self, receiver_twin_did: str, receiver_input_id: str, input_message
    ):
        """Print on screen the Input message received.

        Args:
            receiver_twin_did (str): the Twin DID receiving Input Messages.
            receiver_input_id (str): the Input ID from which the message is received.
            input_message: payload of the Input message received.
        """

        received_data, occurred_at_timestamp = self.input_data_unpack(input_message)

        log.info(
            "Received message %s by Twin DID %s via Input %s at %s",
            received_data,
            receiver_twin_did,
            receiver_input_id,
            occurred_at_timestamp,
        )

    def export_to_db(self, publisher_twin_did: str, publisher_feed_id: str, feed_data):
        """Export to DB the data received.

        Args:
            publisher_twin_did (str): the Twin DID publishing data.
            publisher_feed_id (str): the Feed ID from which the data is published.
            feed_data: Feed data received.
        """

        received_data, occurred_at_timestamp = self.feed_data_unpack(feed_data)

        self._db_writer.store_to_db(
            datetime=occurred_at_timestamp,
            sensor_twin_did=publisher_twin_did,
            sensor_feed_id=publisher_feed_id,
            sensor_reading=received_data.get(constant.SENSOR_FEED_VALUE),
        )

    def grant_db_access(self, full_name: str):
        # Remove any space between name and surname to make the username
        username = full_name.replace(" ", "")
        # Generate a random number made up of 5 digits to make the password
        password = ''.join(random.choices("0123456789", k=5))

        self._db_writer.add_new_user(username=username, password=password)

        return username, password

    def get_from_db(self):
        self._db_reader.get_all_readings()

    def get_list_of_items(self, data_received_queue: Queue) -> List[float]:
        """Append each items of a Queue into a List by emptying the queue.

        Args:
            data_received_queue (Queue): the queue that will be
                emptied and converted into a list.

        Returns:
            List[float]: the list of items converted from a queue.
        """

        items_list: List[float] = []

        try:
            while True:
                # Consume each item of the queue until an 'Empty'
                # exception is received.
                data_received = data_received_queue.get_nowait()

                # Convert the Feed data received into a Python dict
                received_data, _ = self.feed_data_unpack(data_received)
                log.debug("Received data %s from queue", received_data)

                # The data received is a dictionary.
                # We want to get only the list of values from such dictionary.
                new_items = received_data.values()
                log.debug("Adding %s to items_list", new_items)
                items_list.extend(new_items)
        except Empty:
            log.debug("Queue empty")

        return items_list

    def compute_average(self, items_list: List[float]) -> float:
        """Compute the average from a list of items.

        Args:
            items_list (List[float]): the list of items that
                will be used to calculate the average.

        Returns:
            float: the average computed.
        """

        # Compute the average and round the result
        average: float = round(sum(items_list) / len(items_list), 2)

        log.debug("The average data is: %s", average)

        return average

    def get_min_max(self, items_list: List[float]) -> Tuple[float, float]:
        """Compute the Min and Max value from a list of items.

        Args:
            items_list (List[float]): the list of items that
                will be used to calculate the Min/Max.

        Returns:
            Tuple[float, float]: the Min and Max values computed.
        """

        min_value: float = min(items_list)
        max_value: float = max(items_list)

        log.debug("The min/max data is: %s/%s", min_value, max_value)

        return min_value, max_value
