from logging import config

from constants import LOGGING_CONFIGURATION
from data_processor import DataProcessor
from databypass_connector import DataBypassConnector

config.dictConfig(LOGGING_CONFIGURATION)


def main():
    data_processor = DataProcessor()
    databypass_connector = DataBypassConnector(data_processor)
    databypass_connector.start()


if __name__ == "__main__":
    main()
