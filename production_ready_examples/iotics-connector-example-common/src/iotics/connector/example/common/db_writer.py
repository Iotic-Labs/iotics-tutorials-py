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
            log.debug("Creating DB...")
            create_database(self._db_url)
            log.debug("DB created successfully")

        self._initialise()

        Thread(target=self._store).start()

        log.debug("DB Initialised successfully")

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

    def _check_user_exists(self, username: str) -> bool:
        """Check if a user already exists in the database."""

        query = text("SELECT 1 FROM pg_roles WHERE rolname = :username;")
        result = self._session.execute(query, {"username": username})
        return bool(result.scalar())

    def add_new_user(self, username: str, password: str):
        # Check if the user already exists
        user_exists = self._check_user_exists(username)

        if user_exists:
            log.debug("Role %s already exists", username)
            return

        create_new_user_sql = text(f"CREATE USER {username} WITH PASSWORD :password;")
        grant_privileges_sql = text(
            f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {username};"
        )

        try:
            with self._session:
                self._session.execute(create_new_user_sql, {"password": password})
                self._session.execute(grant_privileges_sql)
                self._session.commit()
        except Exception as ex:
            self._session.rollback()
            log.error("An error occurred: %s", ex)
        else:
            log.info(
                "User %s and Password %s created and SELECT privileges granted successfully",
                username,
                password,
            )
