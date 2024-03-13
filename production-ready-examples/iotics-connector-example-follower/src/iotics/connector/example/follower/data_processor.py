import logging

log = logging.getLogger(__name__)


class DataProcessor:
    def print_on_screen(
        self,
        publisher_twin_did: str,
        publisher_feed_id: str,
        occurred_at: str,
        data: dict,
    ):

        log.info(
            "Received data %s published from Twin DID %s via Feed %s at %s",
            data,
            publisher_twin_did,
            publisher_feed_id,
            occurred_at,
        )
