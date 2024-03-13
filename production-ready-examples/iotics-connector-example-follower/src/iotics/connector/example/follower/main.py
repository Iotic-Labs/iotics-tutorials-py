import logging
import sys

from data_processor import DataProcessor
from follower_connector import FollowerConnector

logging.basicConfig(
    level=logging.getLevelName("INFO"),
    format="[%(asctime)s]: %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)

log = logging.getLogger(__name__)


def main():
    data_processor: DataProcessor = DataProcessor()
    follower_connector: FollowerConnector = FollowerConnector(data_processor)
    follower_connector.initialise()
    follower_connector.start()


if __name__ == "__main__":
    main()
