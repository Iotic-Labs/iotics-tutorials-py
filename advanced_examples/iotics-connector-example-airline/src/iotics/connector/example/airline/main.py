import logging
import sys

import constants as constant
from airline_connector import AirlineConnector
from country import Country

logging.basicConfig(
    level=logging.getLevelName("INFO"),
    format="[%(asctime)s]: %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)

log = logging.getLogger(__name__)


def main():
    uk = Country(
        name="UK",
        host_id=constant.UK_HOST_ID,
        lat_min=constant.UK_LAT_MIN,
        lat_max=constant.UK_LAT_MAX,
        lon_min=constant.UK_LON_MIN,
        lon_max=constant.UK_LON_MAX,
    )
    france = Country(
        name="France",
        host_id=constant.FRANCE_HOST_ID,
        lat_min=constant.FRANCE_LAT_MIN,
        lat_max=constant.FRANCE_LAT_MAX,
        lon_min=constant.FRANCE_LON_MIN,
        lon_max=constant.FRANCE_LON_MAX,
    )
    spain = Country(
        name="Spain",
        host_id=constant.SPAIN_HOST_ID,
        lat_min=constant.SPAIN_LAT_MIN,
        lat_max=constant.SPAIN_LAT_MAX,
        lon_min=constant.SPAIN_LON_MIN,
        lon_max=constant.SPAIN_LON_MAX,
    )
    germany = Country(
        name="Germany",
        host_id=constant.GERMANY_HOST_ID,
        lat_min=constant.GERMANY_LAT_MIN,
        lat_max=constant.GERMANY_LAT_MAX,
        lon_min=constant.GERMANY_LON_MIN,
        lon_max=constant.GERMANY_LON_MAX,
    )
    austria = Country(
        name="Austria",
        host_id=constant.AUSTRIA_HOST_ID,
        lat_min=constant.AUSTRIA_LAT_MIN,
        lat_max=constant.AUSTRIA_LAT_MAX,
        lon_min=constant.AUSTRIA_LON_MIN,
        lon_max=constant.AUSTRIA_LON_MAX,
    )

    airline_connector = AirlineConnector(
        countries_list=[uk, france, spain, germany, austria]
    )
    airline_connector.initialise()

    airline_connector.create_new_airline(
        name="ABC",
        legal_name="ABC LTD",
        identifier=constant.AIRLINE_IDENTIFIERS[0],
        hq_country=uk,
        restricted_properties={
            france: [
                constant.ESTIMATED_FLIGHT_DURATION,
                constant.FLIGHT_DEPARTURE_TIME,
            ],
            spain: [
                constant.FLIGHT_MEAL_SERVICE,
                constant.FLIGHT_DEPARTURE_TIME,
            ],
            germany: [
                constant.ESTIMATED_FLIGHT_DURATION,
            ],
            austria: [],
        },
    )
    airline_connector.create_new_airline(
        name="DEF",
        legal_name="DEF LTD",
        identifier=constant.AIRLINE_IDENTIFIERS[1],
        hq_country=spain,
        restricted_properties={
            france: [
                constant.ESTIMATED_FLIGHT_DURATION,
                constant.FLIGHT_DEPARTURE_TIME,
            ],
            spain: [],
            germany: [
                constant.FLIGHT_MEAL_SERVICE,
            ],
            austria: [
                constant.ESTIMATED_FLIGHT_DURATION,
                constant.FLIGHT_DEPARTURE_TIME,
            ],
        },
    )
    
    airline_connector.start()


if __name__ == "__main__":
    main()
