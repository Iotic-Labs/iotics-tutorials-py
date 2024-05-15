import logging
from queue import Queue
from threading import Thread

import constants as constant
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy_utils import create_database, database_exists

Base = declarative_base()
log = logging.getLogger(__name__)


class SensorReading(Base):
    """Model class representing a
        sensor reading Table and attributes.

    Attributes:
        id (int): Primary key.
        timestamp (str): Timestamp of the reading.
        twin_did (str): Identifier for the twin.
        feed_id (str): Identifier for the feed.
        reading (float): The actual sensor reading.
    """

    __tablename__ = "SensorReadings"

    id = Column(Integer, primary_key=True)
    timestamp = Column(String(100))
    twin_did = Column(String(50))
    feed_id = Column(String(50))
    reading = Column(Float)


class DBManager:
    """Manages the database connection and operations."""

    def __init__(self):
        """ "Initialises the DBManager instance,
        sets up the queue, and initializes the database.
        """

        self._session = None
        self._queue = Queue()

        self._initialise_db()

    def _initialise_db(self):
        """Initialises the database and creates tables if they don't exist.
        Additionally, it starts a thread listening for incoming items to store.
        """

        if not database_exists(constant.DB_URL):
            log.info("Creating DB...")
            create_database(constant.DB_URL)
            log.info("DB created successfully")

        log.info("Connecting to DB...")
        engine = create_engine(constant.DB_URL)

        Base.metadata.create_all(engine)
        self._session = Session(engine)

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
