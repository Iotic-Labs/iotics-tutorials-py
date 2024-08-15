import asyncio
from logging import config

from constants import LOGGING_CONFIGURATION
from data_processor import DataProcessor
from follower_connector import FollowerConnector

config.dictConfig(LOGGING_CONFIGURATION)


async def main():
    data_processor = DataProcessor()
    follower_connector = FollowerConnector(data_processor)
    await follower_connector.initialise()
    await follower_connector.start()


if __name__ == "__main__":
    asyncio.run(main())
