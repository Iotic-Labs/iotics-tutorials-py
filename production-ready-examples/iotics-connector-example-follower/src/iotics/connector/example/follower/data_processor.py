import logging

log = logging.getLogger(__name__)


class DataProcessor:
    @staticmethod
    def print_on_screen(
        publisher_twin_did: str,
        publisher_feed_id: str,
        occurred_at: str,
        data: dict,
    ):
        """Print on screen the data received.

        Args:
            publisher_twin_did (str): the Twin DID publishing data.
            publisher_feed_id (str): the Feed ID from which the data is published.
            occurred_at (str): date and time of when the data sample was sent.
            data (dict): data received.
        """

        log.info(
            "Received data %s published by Twin DID %s via Feed %s at %s",
            data,
            publisher_twin_did,
            publisher_feed_id,
            occurred_at,
        )
