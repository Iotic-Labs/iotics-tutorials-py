from logging import config

from constants import LOGGING_CONFIGURATION
from data_source import DataSource
from publisher_connector import PublisherConnector

config.dictConfig(LOGGING_CONFIGURATION)


def main():
    data_source: DataSource = DataSource()
    publisher_connector: PublisherConnector = PublisherConnector(data_source)
    publisher_connector.start()


if __name__ == "__main__":
    main()
