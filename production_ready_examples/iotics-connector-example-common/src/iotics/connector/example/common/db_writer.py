import logging
from queue import Queue
from threading import Thread

from db_manager import DBManager, SensorReading
from sqlalchemy import text
from sqlalchemy_utils import create_database, database_exists

log = logging.getLogger(__name__)


class DBWriter(DBManager):
    """Manages the database connection and operations."""

    def __init__(self, db_name: str, db_username: str, db_password: str):
        """ "Initialises the DBManager instance,
        sets up the queue, and initializes the database.
        """

        super().__init__(
            db_username=db_username, db_password=db_password, db_name=db_name
        )

        self._queue = Queue()
        self._initialise_db()

    def _initialise_db(self):
        """Initialises the database and creates tables if they don't exist.
        Additionally, it starts a thread listening for incoming items to store.
        """

        if not database_exists(self._db_url):
            log.info("Creating DB...")
            create_database(self._db_url)
            log.info("DB created successfully")

        self._initialise()

        Thread(target=self._store).start()

        log.info("DB Initialised successfully")

    def _store(self):
        """Background thread method that continuously stores sensor readings
        from the queue to the database.
        """

        log.debug("Waiting for incoming items to store...")

        while True:
            sensor_reading: SensorReading = self._queue.get()

            try:
                self._session.add(sensor_reading)
                self._session.commit()
            except Exception as ex:
                log.error("Error storing item: %s", ex)
                self._session.rollback()
            else:
                log.debug("Item stored successfully")

    def store_to_db(
        self,
        datetime: str,
        sensor_twin_did: str,
        sensor_feed_id: str,
        sensor_reading: dict,
    ):
        """Adds a sensor reading to the queue for storage.

        Args:
            datetime (str): The timestamp of the reading.
            sensor_twin_did (str): The twin ID that shared the data.
            sensor_feed_id (str): The feed ID that the data was shared from.
            sensor_reading (dict): The sensor reading data.
        """

        sensor_reading_obj = SensorReading(
            timestamp=datetime,
            twin_did=sensor_twin_did,
            feed_id=sensor_feed_id,
            reading=sensor_reading,
        )

        self._queue.put(sensor_reading_obj)
        log.debug("Item added to the queue")

    def add_new_user(self, username: str, password: str):
        create_new_user_sql = text(f"CREATE USER {username} WITH PASSWORD :password;")
        grant_privileges_sql = text(f"GRANT ALL PRIVILEGES ON DATABASE {self._db_name} TO {username};")

        try:
            self._session.execute(create_new_user_sql, {'password': password})
            self._session.execute(grant_privileges_sql)
            self._session.commit()
        except Exception as ex:
            self._session.rollback()
            log.error("An error occurred: %s", ex)
        else:
            log.info("User %s created and privileges granted successfully", username)
        finally:
            self._session.close()
