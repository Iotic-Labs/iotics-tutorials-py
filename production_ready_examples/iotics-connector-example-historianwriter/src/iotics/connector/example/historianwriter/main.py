from logging import config

from constants import LOGGING_CONFIGURATION
from data_processor import DataProcessor
from historian_writer_connector import HistorianWriterConnector

config.dictConfig(LOGGING_CONFIGURATION)


def main():
    data_processor = DataProcessor()
    historian_writer_connector = HistorianWriterConnector(data_processor)
    historian_writer_connector.start()


if __name__ == "__main__":
    main()
