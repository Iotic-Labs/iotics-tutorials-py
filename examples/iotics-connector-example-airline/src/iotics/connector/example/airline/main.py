import logging
import sys

from airline_connector import AirlineConnector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


def main():
    airline_connector_1 = AirlineConnector(
        airline_name="Airline ABC",
        legal_name="Airline ABC LTD",
        airline_identifier="AL1",
        airline_hq_location="UK",
    )
    airline_connector_1.initialise()
    airline_connector_1.start()


if __name__ == "__main__":
    main()
