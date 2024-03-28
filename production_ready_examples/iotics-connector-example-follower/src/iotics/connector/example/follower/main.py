from logging import config

from constants import LOGGING_CONFIGURATION
from data_processor import DataProcessor
from follower_connector import FollowerConnector

config.dictConfig(LOGGING_CONFIGURATION)


def main():
    data_processor: DataProcessor = DataProcessor()
    follower_connector: FollowerConnector = FollowerConnector(data_processor)
    follower_connector.start()


if __name__ == "__main__":
    main()
