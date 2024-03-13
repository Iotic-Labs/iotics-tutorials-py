import logging
from random import randint

import constants as constant

log = logging.getLogger(__name__)


class DataSource:
    def make_sensor_reading(self) -> int:
        rand_temperature: int = randint(constant.MIN_VALUE, constant.MAX_VALUE)
        log.debug("Generated sensor reading of %d", rand_temperature)

        return rand_temperature
