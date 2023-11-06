import logging
import os
import sys
from datetime import datetime, timedelta
from random import uniform
from threading import Thread
from time import sleep

import constants as constant
from identity import Identity
from iotics.lib.grpc.helpers import (
    create_feed_with_meta,
    create_location,
    create_property,
    create_value,
)
from iotics.lib.grpc.iotics_api import IoticsApi
from utilities import auto_refresh_token, get_host_endpoints

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class FlightConnector:
    def __init__(
        self,
        number: str,
        departure_airport: str,
        departure_time: datetime,
        arrival_airport: str,
        estimated_flight_duration: timedelta,
        airline_identifier: str,
    ):
        self._iotics_api: IoticsApi = None
        self._iotics_identity: Identity = None
        self._flight_number: str = number
        self._departure_airport: str = departure_airport
        self._departure_time: datetime = departure_time
        self._arrival_airport: str = arrival_airport
        self._estimated_flight_duration: timedelta = estimated_flight_duration
        self._airline_identifier: str = airline_identifier
        self._flight_twin_did: str = None

    def _initialise(self):
        endpoints = get_host_endpoints(host_url=os.getenv("FLIGHT_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("FLIGHT_AGENT_KEY_NAME"),
            agent_seed=os.getenv("FLIGHT_AGENT_SEED"),
        )
        self._iotics_api = IoticsApi(auth=self._iotics_identity)

        # Auto-generate a new token when it expires
        Thread(
            target=auto_refresh_token,
            args=[self._iotics_identity, self._iotics_api],
            daemon=True,
        ).start()

    def _create_twin_model(self):
        logging.info("Creating Twin Model...")
        # Generate a new Twin Registered Identity for the Flight Twin Model
        flight_twin_model_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name="FlightTwinModel"
            )
        )

        # Define Twin Model's Metadata
        twin_model_properties = [
            create_property(key=constant.TYPE, value=constant.TWIN_MODEL, is_uri=True),
            create_property(key=constant.CREATED_BY, value="Flight Connector Example"),
            create_property(key=constant.UPDATED_BY, value="Flight Connector Example"),
            create_property(
                key=constant.LABEL,
                value=constant.FLIGHT_TWIN_MODEL_LABEL,
                language="en",
            ),
            create_property(
                key=constant.DEFINES, value=constant.FLIGHT_ONTOLOGY, is_uri=True
            ),
            create_property(
                key=constant.HAS_PROJECT_NAME,
                value=constant.PROJECT_NAME,
                language="en",
            ),
        ]

        # Define Twin Feed's Input
        feeds = [
            create_feed_with_meta(
                input_id=constant.FLIGHT_FEED_ID,
                properties=[
                    create_property(
                        key=constant.LABEL,
                        value="New flight's coordinates",
                        language="en",
                    )
                ],
                values=[
                    create_value(
                        label=constant.FLIGHT_FEED_LABEL_LAT,
                        comment="Flight's new latitude",
                        data_type="float",
                    ),
                    create_value(
                        label=constant.FLIGHT_FEED_LABEL_LON,
                        comment="Flight's new longitude",
                        data_type="float",
                    ),
                ],
            ),
        ]

        # Upsert Twin
        self._iotics_api.upsert_twin(
            twin_did=flight_twin_model_identity.did,
            properties=twin_model_properties,
            feeds=feeds,
        )

        logging.info(
            "%s Twin created: %s",
            constant.FLIGHT_TWIN_MODEL_LABEL,
            flight_twin_model_identity.did,
        )

    def _search_twin_model(self):
        logging.info("Searching for Flight Twin Model ...")

        # Search for the Flight Twin Model
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.TWIN_MODEL, is_uri=True
                ),
                create_property(
                    key=constant.DEFINES, value=constant.FLIGHT_ONTOLOGY, is_uri=True
                ),
                create_property(
                    key=constant.HAS_PROJECT_NAME,
                    value=constant.PROJECT_NAME,
                    language="en",
                ),
            ],
            response_type="FULL",
        )

        twins_found_list = []
        # Keep searching until the Twin Model is found.
        # The latter could be created after this search operation is executed.
        attempts: int = 0
        while True:
            for response in self._iotics_api.search_iter(
                client_app_id=self._flight_number, payload=search_criteria
            ):
                twins = response.payload.twins
                twins_found_list.extend(twins)

            if not twins_found_list:
                if attempts < 3:
                    logging.info(
                        "Twin Model not found based on the search criteria. Trying again in 5s"
                    )
                    sleep(5)
                    attempts += 1
                else:
                    self._create_twin_model()
            else:
                break

        twin_model = next(iter(twins_found_list))

        return twin_model

    def _create_twin_from_model(
        self, flight_twin_model, departure_airport_coords: dict
    ):
        logging.info("Creating Flight Twin for %s ...", self._flight_number)

        twin_model_id = flight_twin_model.twinId.id
        twin_model_properties = flight_twin_model.properties
        twin_model_feeds = flight_twin_model.feeds

        airline_twin = self._search_airline_twin()

        twin_properties = [
            create_property(
                key=constant.TWIN_FROM_MODEL, value=twin_model_id, is_uri=True
            ),
            create_property(
                key=constant.LABEL, value=self._flight_number, language="en"
            ),
            create_property(
                key=constant.TYPE, value=constant.FLIGHT_ONTOLOGY, is_uri=True
            ),
            create_property(
                key=constant.FLIGHT_ARRIVAL_AIRPORT, value=self._arrival_airport
            ),
            create_property(
                key=constant.FLIGHT_ARRIVAL_TIME,
                value=self._departure_time + self._estimated_flight_duration,
            ),
            create_property(
                key=constant.FLIGHT_DEPARTURE_AIRPORT, value=self._departure_airport
            ),
            create_property(
                key=constant.FLIGHT_DEPARTURE_TIME, value=self._departure_time
            ),
            create_property(
                key=constant.FLIGHT_ESTIMATED_FLIGHT_DURATION,
                value=self._estimated_flight_duration,
            ),
            create_property(
                key=constant.FLIGHT_PROVIDER, value=airline_twin.twinId.id, is_uri=True
            ),
            create_property(key=constant.FLIGHT_NUMBER, value=self._flight_number),
        ]

        # The Flight Twin's Properties will be the same as the Twin Models',
        # except the ones we defined above and some other exceptions.
        for twin_model_property in twin_model_properties:
            if twin_model_property.key in [
                constant.TYPE,
                constant.LABEL,
                constant.DEFINES,
            ]:
                continue

            twin_properties.append(twin_model_property)

        twin_feeds = []
        for twin_feed in twin_model_feeds:
            feed_id = twin_feed.feedId.id
            feed_description = self._iotics_api.describe_feed(
                twin_did=twin_model_id, feed_id=feed_id
            )
            twin_feeds.append(
                create_feed_with_meta(
                    feed_id=feed_id,
                    properties=twin_feed.properties,
                    values=feed_description.payload.result.values,
                )
            )

        # Generate a new Twin Registered Identity for the Flight Twin
        flight_twin_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name=self._flight_number
            )
        )

        self._flight_twin_did = flight_twin_identity.did

        # Upsert Twin
        self._iotics_api.upsert_twin(
            twin_did=self._airline_twin_did,
            properties=twin_properties,
            feeds=twin_feeds,
            location=create_location(
                lat=departure_airport_coords.get("lat"),
                lon=departure_airport_coords.get("lon"),
            ),
        )

        logging.info(
            "%s Flight Twin created: %s", self._flight_number, self._flight_twin_did
        )

    def _search_airline_twin(self):
        logging.info("Searching for Airline %s Twin ...", self._airline_identifier)

        # Search for the Flight Twin Model
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.AIRLINE_ONTOLOGY, is_uri=True
                ),
                create_property(
                    key=constant.AIRLINE_IDENTIFIER, value=self._airline_identifier
                ),
            ],
            response_type="FULL",
        )

        twins_found_list = []
        # Keep searching until the Airline Twin is found.
        # The latter could be created after this search operation is executed.
        while True:
            for response in self._iotics_api.search_iter(
                client_app_id=self._flight_number, payload=search_criteria
            ):
                twins = response.payload.twins
                twins_found_list.extend(twins)

            if not twins_found_list:
                logging.info(
                    "Twin not found based on the search criteria. Trying again in 5s"
                )
                sleep(5)
            else:
                break

        airline_twin = next(iter(twins_found_list))

        return airline_twin

    def _start_flight(
        self, departure_airport_coords: dict, arrival_airport_coords: dict
    ):
        departure_lat = departure_airport_coords.get("lat")
        departure_lon = departure_airport_coords.get("lon")
        arrival_lat = arrival_airport_coords.get("lat")
        arrival_lon = arrival_airport_coords.get("lon")

        last_lat = departure_lat
        last_lon = departure_lon

        while True:
            try:
                new_lat = uniform(last_lat, arrival_lat)
                new_lon = uniform(last_lon, arrival_lon)

                if new_lat == arrival_lat and new_lon == arrival_lon:
                    logging.info("Flight completed")
                    break

                self._iotics_api.share_feed_data(
                    twin_did=self._flight_twin_did,
                    feed_id=constant.FLIGHT_FEED_ID,
                    data={
                        constant.FLIGHT_FEED_LABEL_LAT: new_lat,
                        constant.FLIGHT_FEED_LABEL_LON: new_lon,
                    },
                )

                self._iotics_api.update_twin(
                    twin_did=self._flight_twin_did,
                    location=create_location(lat=new_lat, lon=new_lon),
                )

                sleep(constant.FLIGHT_SHARING_PERIOD_SEC)

                last_lat = new_lat
                last_lon = new_lon
            except KeyboardInterrupt:
                logging.info("Exiting flight connector")
                break

    def start(self):
        flight_twin_model = self._search_twin_model()
        departure_airport_coords: dict = constant.FLIGHT_COORDINATES.get(
            self._departure_airport
        )
        arrival_airport_coords: dict = constant.FLIGHT_COORDINATES.get(
            self._arrival_airport
        )
        self._create_twin_from_model(
            flight_twin_model=flight_twin_model,
            departure_airport_coords=departure_airport_coords,
        )
        self._start_flight(
            departure_airport_coords=departure_airport_coords,
            arrival_airport_coords=arrival_airport_coords,
        )
