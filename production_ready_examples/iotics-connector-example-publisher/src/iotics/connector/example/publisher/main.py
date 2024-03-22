import logging
import sys

from data_source import DataSource
from publisher_connector import PublisherConnector

logging.basicConfig(
    level=logging.getLevelName("INFO"),
    format="[%(asctime)s]: %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)

log = logging.getLogger(__name__)


def main():
    data_source: DataSource = DataSource()
    publisher_connector: PublisherConnector = PublisherConnector(data_source)
    publisher_connector.start()


if __name__ == "__main__":
    main()
