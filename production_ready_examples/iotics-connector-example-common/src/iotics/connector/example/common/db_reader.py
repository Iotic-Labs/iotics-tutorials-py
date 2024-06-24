import logging

from db_manager import DBManager, SensorReading

log = logging.getLogger(__name__)


class DBReader(DBManager):
    def __init__(self, db_name: str, db_username: str, db_password: str):
        super().__init__(
            db_username=db_username, db_password=db_password, db_name=db_name
        )

    def initialise_db(self):
        self._initialise()

        return self._is_initialised

    def select_all_readings_from_db(self):
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
