import json
import logging
from datetime import datetime

log = logging.getLogger(__name__)


class DataProcessor:
    """Object simulating a data processor."""

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
