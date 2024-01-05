import logging
import os
import sys
from datetime import datetime, timedelta
from random import uniform
from threading import Lock, Thread
from time import sleep
from typing import List

import constants as constant
import grpc
from flight import Flight
from identity import Identity
from iotics.lib.grpc.helpers import (
    create_feed_with_meta,
    create_location,
    create_property,
    create_value,
)
from iotics.lib.grpc.iotics_api import IoticsApi
from utilities import (
    auto_refresh_token,
    get_host_endpoints,
    is_token_expired,
    search_twins,
)

log = logging.getLogger(__name__)


class FlightConnector:
    def __init__(self):
        self._iotics_api: IoticsApi = None
        self._iotics_identity: Identity = None
        self._refresh_token_lock: Lock = None
        self._flight_twin_model = None
        self._flights_dict: dict = None

    def initialise(self):
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
        self._refresh_token_lock = Lock()
        self._flights_dict = {}

        # Auto-generate a new token when it expires
        Thread(
            target=auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_identity, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

        self._clear_space()
        self._create_flight_twin_model()
        self._search_flight_twin_model()

    def _clear_space(self):
        log.info("Deleting old Flight Twins...")

        # Search for Flight Twins
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.FLIGHT_ONTOLOGY, is_uri=True
                ),
            ],
            response_type="FULL",
        )

        twins_found_list = search_twins(
            search_criteria, self._refresh_token_lock, self._iotics_api, False
        )

        for twin in twins_found_list:
            twin_did = twin.twinId.id
            self._iotics_api.delete_twin(twin_did)

    def _create_flight_twin_model(self):
        log.info("Creating Flight Twin Model...")
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

        # Define Twin's Feeds
        feeds = [
            create_feed_with_meta(
                feed_id=constant.FLIGHT_FEED_ID,
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

        try:
            with self._refresh_token_lock:
                self._iotics_api.upsert_twin(
                    twin_did=flight_twin_model_identity.did,
                    properties=twin_model_properties,
                    feeds=feeds,
                )
        except grpc.RpcError as ex:
            if not is_token_expired(exception=ex, operation="create_twin_model"):
                sys.exit(1)

        log.info(
            "%s Twin created: %s",
            constant.FLIGHT_TWIN_MODEL_LABEL,
            flight_twin_model_identity.did,
        )

    def _search_flight_twin_model(self):
        log.info("Searching for Flight Twin Model...")

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

        twins_found_list = search_twins(
            search_criteria, self._refresh_token_lock, self._iotics_api
        )
        self._flight_twin_model = next(iter(twins_found_list))

    def _create_twin_from_model(self, flight: Flight, airline_twin: str) -> str:
        log.debug("Creating Flight Twin %s", flight.number)

        twin_model_id = self._flight_twin_model.twinId.id
        twin_model_properties = self._flight_twin_model.properties
        twin_model_feeds = self._flight_twin_model.feeds

        twin_properties = [
            create_property(
                key=constant.TWIN_FROM_MODEL, value=twin_model_id, is_uri=True
            ),
            create_property(key=constant.LABEL, value=flight.number, language="en"),
            create_property(
                key=constant.TYPE, value=constant.FLIGHT_ONTOLOGY, is_uri=True
            ),
            create_property(
                key=constant.FLIGHT_ARRIVAL_AIRPORT,
                value=flight.arrival_airport.get("name"),
            ),
            create_property(key=constant.FLIGHT_AIRCRAFT, value="Boeing 737"),
            create_property(key=constant.FLIGHT_MEAL_SERVICE, value="Full Board"),
            create_property(
                key=constant.FLIGHT_ARRIVAL_TIME,
                value=str(flight.departure_time + flight.estimated_flight_duration),
            ),
            create_property(
                key=constant.FLIGHT_DEPARTURE_AIRPORT,
                value=flight.departure_airport.get("name"),
            ),
            create_property(
                key=constant.FLIGHT_DEPARTURE_TIME, value=str(flight.departure_time)
            ),
            create_property(
                key=constant.ESTIMATED_FLIGHT_DURATION,
                value=str(flight.estimated_flight_duration),
            ),
            create_property(
                key=constant.FLIGHT_PROVIDER, value=airline_twin.twinId.id, is_uri=True
            ),
            create_property(key=constant.FLIGHT_NUMBER, value=flight.number),
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

            try:
                with self._refresh_token_lock:
                    feed_description = self._iotics_api.describe_feed(
                        twin_did=twin_model_id, feed_id=feed_id
                    )
            except grpc.RpcError as ex:
                if not is_token_expired(exception=ex, operation="describe_feed"):
                    sys.exit(1)

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
                twin_key_name=flight.number
            )
        )
        flight_twin_id = flight_twin_identity.did
        departure_airport_coords = flight.departure_airport.get("coords")

        try:
            with self._refresh_token_lock:
                self._iotics_api.upsert_twin(
                    twin_did=flight_twin_id,
                    properties=twin_properties,
                    feeds=twin_feeds,
                    location=create_location(
                        lat=departure_airport_coords.get("lat"),
                        lon=departure_airport_coords.get("lon"),
                    ),
                )
        except grpc.RpcError as ex:
            if not is_token_expired(exception=ex, operation="create_twin_from_model"):
                sys.exit(1)

        log.info("%s Flight Twin created: %s", flight.number, flight_twin_id)

        return flight_twin_id

    def _search_airline_twin(self, airline_identifier: str):
        log.info("Searching for %s Twin ...", airline_identifier)

        # Search for the Flight Twin Model
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.AIRLINE_ONTOLOGY, is_uri=True
                ),
                create_property(
                    key=constant.AIRLINE_IDENTIFIER, value=airline_identifier
                ),
            ],
            response_type="FULL",
        )

        twins_found_list = search_twins(
            search_criteria, self._refresh_token_lock, self._iotics_api
        )
        airline_twin = next(iter(twins_found_list))

        return airline_twin

    def _start_flight(self, flight_twin_id: str, flight: Flight):
        departure_airport_coords = flight.departure_airport.get("coords")
        departure_lat = departure_airport_coords.get("lat")
        departure_lon = departure_airport_coords.get("lon")

        arrival_airport_coords = flight.arrival_airport.get("coords")
        arrival_lat = arrival_airport_coords.get("lat")
        arrival_lon = arrival_airport_coords.get("lon")

        last_lat = departure_lat
        last_lon = departure_lon

        while True:
            new_lat = round(uniform(last_lat, arrival_lat), 4)
            new_lon = round(uniform(last_lon, arrival_lon), 4)

            try:
                with self._refresh_token_lock:
                    self._iotics_api.share_feed_data(
                        twin_did=flight_twin_id,
                        feed_id=constant.FLIGHT_FEED_ID,
                        data={
                            constant.FLIGHT_FEED_LABEL_LAT: new_lat,
                            constant.FLIGHT_FEED_LABEL_LON: new_lon,
                        },
                    )
            except grpc.RpcError as ex:
                if not is_token_expired(exception=ex, operation="start_flight"):
                    sys.exit(1)

            log.info("Flight %s moved to (%.4f, %.4f)", flight.number, new_lat, new_lon)
            last_lat = new_lat
            last_lon = new_lon

            if new_lat == arrival_lat and new_lon == arrival_lon:
                log.info("Flight %s completed", flight.number)
                self._iotics_api.delete_twin(twin_did=flight_twin_id)
                break

            sleep(constant.FLIGHT_SHARING_PERIOD_SEC)

    def create_new_flight(
        self,
        number: str,
        departure_airport: str,
        departure_time: datetime,
        arrival_airport: str,
        estimated_flight_duration: timedelta,
        airline_identifier: str,
    ):
        flight = Flight(
            number,
            departure_airport,
            departure_time,
            arrival_airport,
            estimated_flight_duration,
            airline_identifier,
        )
        airline_twin = self._search_airline_twin(airline_identifier)
        flight_twin_id = self._create_twin_from_model(flight, airline_twin)
        self._flights_dict.update({flight_twin_id: flight})

    def start(self):
        # threads_list: List[Thread] = []
        for flight_twin_id, flight in self._flights_dict.items():
            th = Thread(target=self._start_flight, args=[flight_twin_id, flight])
            th.start()

        # for th in threads_list:
        #     th.join()

        self._iotics_api.delete_twin(twin_did=self._flight_twin_model.twinId.id)
