import json
import logging
from datetime import datetime

import constants as constant
from db_manager import DBManager

log = logging.getLogger(__name__)


class DataProcessor:
    """Object simulating a data processor."""

    def __init__(self):
        self._db_manager = DBManager()

    @staticmethod
    def print_on_screen(
        publisher_twin_did: str, publisher_feed_id: str, feed_data_payload
    ):
        """Print on screen the data received.

        Args:
            publisher_twin_did (str): the Twin DID publishing data.
            publisher_feed_id (str): the Feed ID from which the data is published.
            feed_data_payload: payload of the Feed data received.
        """

        received_data = json.loads(feed_data_payload.feedData.data)
        occurred_at_unix_time = feed_data_payload.feedData.occurredAt.seconds
        occurred_at_timestamp = str(datetime.fromtimestamp(occurred_at_unix_time))

        log.info(
            "Received data %s published by Twin DID %s via Feed %s at %s",
            received_data,
            publisher_twin_did,
            publisher_feed_id,
            occurred_at_timestamp,
        )

    def export_to_db(
        self, publisher_twin_did: str, publisher_feed_id: str, feed_data_payload
    ):
        """Export to DB the data received.

        Args:
            publisher_twin_did (str): the Twin DID publishing data.
            publisher_feed_id (str): the Feed ID from which the data is published.
            feed_data_payload: payload of the Feed data received.
        """

        received_data: dict = json.loads(feed_data_payload.feedData.data)
        occurred_at_unix_time = feed_data_payload.feedData.occurredAt.seconds
        occurred_at_timestamp = str(datetime.fromtimestamp(occurred_at_unix_time))

        self._db_manager.store_to_db(
            datetime=occurred_at_timestamp,
            sensor_twin_did=publisher_twin_did,
            sensor_feed_id=publisher_feed_id,
            sensor_reading=received_data.get(constant.SENSOR_FEED_VALUE),
        )
