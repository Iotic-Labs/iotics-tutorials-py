import logging

import constants as constant
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from utilities import check_global_var

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
    def __init__(self, db_name: str, db_username: str, db_password: str):
        check_global_var(var=db_name, var_name="DB_NAME")
        check_global_var(var=db_username, var_name="DB_USERNAME")
        check_global_var(var=db_password, var_name="POSTGRES_PASSWORD")

        self._session: Session = None

        self._db_name: str = db_name
        self._db_username: str = db_username
        self._db_password: str = db_password
        self._db_url: str = constant.DB_URL.format(
            username=self._db_username, password=self._db_password, db_name=db_name
        )

    def _initialise(self):
        log.debug("Connecting to DB...")
        engine = create_engine(self._db_url)

        try:
            Base.metadata.create_all(engine)
        except Exception as ex:
            log.error("Exception raised in initialising DB: %s", ex)
        else:
            self._session = Session(engine)
            log.debug("Connected to DB")
