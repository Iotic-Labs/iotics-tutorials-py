import logging
from random import randint, uniform
from time import sleep

import constants as constant

log = logging.getLogger(__name__)


class DataSource:
    def make_temperature_reading(self) -> dict:
        sleep(constant.TEMPERATURE_READING_PERIOD)

        rand_temperature: float = round(
            uniform(constant.MIN_TEMP_VALUE, constant.MAX_TEMP_VALUE), 2
        )
        log.debug("Generated temperature reading of %d", rand_temperature)

        temperature_data: dict = {constant.SENSOR_VALUE_LABEL: rand_temperature}

        return temperature_data

    def make_humidity_reading(self) -> dict:
        sleep(constant.HUMIDITY_READING_PERIOD)

        rand_humidity: int = randint(constant.MIN_HUM_VALUE, constant.MAX_HUM_VALUE)
        log.debug("Generated humidity reading of %d", rand_humidity)

        humidity_data: dict = {constant.SENSOR_VALUE_LABEL: rand_humidity}

        return humidity_data
