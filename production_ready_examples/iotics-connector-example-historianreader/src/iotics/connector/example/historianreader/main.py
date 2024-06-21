from logging import config

from constants import LOGGING_CONFIGURATION
from data_processor import DataProcessor
from historian_reader_connector import HistorianReaderConnector

config.dictConfig(LOGGING_CONFIGURATION)


def main():
    data_processor = DataProcessor()
    historian_reader_connector = HistorianReaderConnector(data_processor)
    historian_reader_connector.start()


if __name__ == "__main__":
    main()
