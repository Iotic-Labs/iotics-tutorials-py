import logging
import sys

from airline_connector import AirlineConnector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


def main():
    airline_connector_micky_mouse = AirlineConnector(
        airline_name="micky_mouse",
        legal_name="Micky Mouse LTD",
        airline_identifier="AL1",
        airline_hq_location="UK",
    )
    airline_connector_micky_mouse.initialise()
    airline_connector_micky_mouse.start()


if __name__ == "__main__":
    main()
