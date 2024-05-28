from logging import config

from constants import LOGGING_CONFIGURATION
from data_processor import DataProcessor
from synthesiser_connector import SynthesiserConnector

config.dictConfig(LOGGING_CONFIGURATION)


def main():
    data_processor = DataProcessor()
    synthesiser_connector = SynthesiserConnector(data_processor)
    synthesiser_connector.start()


if __name__ == "__main__":
    main()
