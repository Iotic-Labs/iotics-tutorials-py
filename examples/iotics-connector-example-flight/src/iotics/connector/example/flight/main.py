import logging
import sys
from datetime import datetime, timedelta

import constants as constant
from flight_connector import FlightConnector

logging.basicConfig(
    level=logging.getLevelName("INFO"),
    format="[%(asctime)s] %(levelname)s %(funcName)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)

log = logging.getLogger(__name__)


def main():
    flight_connector = FlightConnector()
    flight_connector.initialise()

    flight_connector.create_new_flight(
        number="ABC123",
        departure_airport=constant.AIRPORT_COORDINATES[0],
        arrival_airport=constant.AIRPORT_COORDINATES[1],
        departure_time=datetime.now() + timedelta(hours=1),
        estimated_flight_duration=timedelta(hours=1, minutes=45),
        airline_identifier=constant.AIRLINE_IDENTIFIERS[0],
    )
    flight_connector.create_new_flight(
        number="DEF456",
        departure_airport=constant.AIRPORT_COORDINATES[1],
        arrival_airport=constant.AIRPORT_COORDINATES[3],
        departure_time=datetime.now() + timedelta(hours=2),
        estimated_flight_duration=timedelta(hours=1),
        airline_identifier=constant.AIRLINE_IDENTIFIERS[1],
    )
    flight_connector.create_new_flight(
        number="GHI789",
        departure_airport=constant.AIRPORT_COORDINATES[4],
        arrival_airport=constant.AIRPORT_COORDINATES[0],
        departure_time=datetime.now() + timedelta(minutes=30),
        estimated_flight_duration=timedelta(hours=2),
        airline_identifier=constant.AIRLINE_IDENTIFIERS[2],
    )

    flight_connector.start()


if __name__ == "__main__":
    main()
