import logging
from datetime import datetime

import constants as constant
from db_manager import DBManager, SensorReading
from sqlalchemy import and_

log = logging.getLogger(__name__)


class DBReader(DBManager):
    def __init__(self, db_name: str, db_username: str, db_password: str):
        super().__init__(
            db_username=db_username, db_password=db_password, db_name=db_name
        )
        self._initialise()

    def select_all_readings(self):
        """Fetches all sensor readings from the database.

        Returns:
            list: A list of SensorReading objects.
        """

        readings = []

        try:
            with self._session:
                readings = self._session.query(SensorReading).all()
        except Exception as ex:
            log.error("Error fetching all readings: %s", ex)
        else:
            log.debug("Fetched all readings successfully")

        return readings

    def select_readings_in_datetime_range(
        self, start_datetime: datetime, end_datetime: datetime
    ):
        """Fetches sensor readings from the database within a specified datetime range.

        Args:
            start_datetime (str): The start datetime .
            end_datetime (str): The end datetime.

        Returns:
            list: A list of SensorReading objects within the specified datetime range.
        """

        readings = []

        try:
            with self._session:
                # Filter readings based on the datetime range
                readings = (
                    self._session.query(SensorReading)
                    .filter(
                        and_(
                            SensorReading.timestamp
                            >= start_datetime.strftime(constant.DATETIME_FORMAT),
                            SensorReading.timestamp
                            <= end_datetime.strftime(constant.DATETIME_FORMAT),
                        )
                    )
                    .all()
                )
        except Exception as ex:
            log.error("Error fetching readings in range: %s", ex)
        else:
            log.debug("Fetched readings in range successfully")

        return readings
