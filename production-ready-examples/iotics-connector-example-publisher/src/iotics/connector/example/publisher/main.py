import logging
import sys

from publisher_connector import PublisherConnector

logging.basicConfig(
    level=logging.getLevelName("INFO"),
    format="[%(asctime)s]: %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)

log = logging.getLogger(__name__)


def main():
    publisher_connector = PublisherConnector()
    publisher_connector.initialise()
    publisher_connector.start()


if __name__ == "__main__":
    main()
