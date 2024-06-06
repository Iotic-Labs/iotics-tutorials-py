import logging

from db_manager import DBManager, SensorReading

log = logging.getLogger(__name__)


class DBReader(DBManager):
    def __init__(self, db_name: str, db_username: str, db_password: str):
        super().__init__(
            db_username=db_username, db_password=db_password, db_name=db_name
        )

        self._initialise()

    def get_all_readings(self):
        """Fetches all sensor readings from the database.

        Returns:
            list: A list of SensorReading objects.
        """

        readings = []

        try:
            readings = self._session.query(SensorReading).all()
            log.debug("Fetched all readings successfully")
        except Exception as ex:
            log.error("Error fetching all readings: %s", ex)

        for reading in readings:
            print(reading.timestamp, reading.twin_did, reading.feed_id, reading.reading)

        return readings
