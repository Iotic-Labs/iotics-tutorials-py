import json
import logging
import os
import sys
from threading import Lock, Thread
from time import sleep
from typing import List

import constants as constant
import grpc
from airline import Airline
from country import Country
from identity import Identity
from iotics.lib.grpc.helpers import create_property, create_feed_with_meta, create_value
from iotics.lib.grpc.iotics_api import IoticsApi
from utilities import (
    auto_refresh_token,
    get_host_endpoints,
    is_token_expired,
    search_twins,
)

log = logging.getLogger(__name__)


class AirlineConnector:
    def __init__(self, countries_list: List[Country]):
        self._countries_list: List[Country] = countries_list
        self._iotics_api: IoticsApi = None
        self._iotics_identity: Identity = None
        self._refresh_token_lock: Lock = None
        self._airlines_list: List[Airline] = None
        self._flights_shadow: dict = None
        self._airline_twin_model = None

    def initialise(self):
        endpoints = get_host_endpoints(host_url=os.getenv("AIRLINE_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("AIRLINE_AGENT_KEY_NAME"),
            agent_seed=os.getenv("AIRLINE_AGENT_SEED"),
        )
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        self._airlines_dict = {}
        self._flights_shadow = {}
        self._refresh_token_lock = Lock()

        # Auto-generate a new token when it expires
        Thread(
            target=auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_identity, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

        self._clear_space()
        self._create_twin_model()
        self._search_airline_twin_model()

    def _clear_space(self):
        log.info("Deleting old Airline Twins...")

        # Search for Airline Twins
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.AIRLINE_ONTOLOGY, is_uri=True
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

    def _create_twin_model(self):
        log.info("Creating Airline Twin Model...")
        # Generate a new Twin Registered Identity for the Airline Twin Model
        airline_twin_model_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name="AirlineTwinModel"
            )
        )

        # Define Twin Model's Metadata
        twin_model_properties = [
            create_property(key=constant.TYPE, value=constant.TWIN_MODEL, is_uri=True),
            create_property(key=constant.CREATED_BY, value="Airline Connector Example"),
            create_property(key=constant.UPDATED_BY, value="Airline Connector Example"),
            create_property(
                key=constant.LABEL,
                value=constant.AIRLINE_TWIN_MODEL_LABEL,
                language="en",
            ),
            create_property(
                key=constant.DEFINES, value=constant.AIRLINE_ONTOLOGY, is_uri=True
            ),
            create_property(
                key=constant.HAS_PROJECT_NAME,
                value=constant.PROJECT_NAME,
                language="en",
            ),
        ]

        try:
            with self._refresh_token_lock:
                self._iotics_api.upsert_twin(
                    twin_did=airline_twin_model_identity.did,
                    properties=twin_model_properties,
                )
        except grpc.RpcError as ex:
            if not is_token_expired(exception=ex, operation="create_twin_model"):
                sys.exit(1)

        log.info(
            "%s Twin created: %s",
            constant.AIRLINE_TWIN_MODEL_LABEL,
            airline_twin_model_identity.did,
        )

    def _search_airline_twin_model(self):
        log.info("Searching for Airline Twin Model...")

        # Search for the Airline Twin Model
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.TWIN_MODEL, is_uri=True
                ),
                create_property(
                    key=constant.DEFINES, value=constant.AIRLINE_ONTOLOGY, is_uri=True
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
        self._airline_twin_model = next(iter(twins_found_list))

    def _create_twin_from_model(self, airline: Airline) -> str:
        log.info("Creating Airline Twin %s ...", airline.name)

        twin_model_id = self._airline_twin_model.twinId.id
        twin_model_properties = self._airline_twin_model.properties

        twin_properties = [
            create_property(
                key=constant.TWIN_FROM_MODEL, value=twin_model_id, is_uri=True
            ),
            create_property(key=constant.LABEL, value=airline.name, language="en"),
            create_property(
                key=constant.TYPE, value=constant.AIRLINE_ONTOLOGY, is_uri=True
            ),
            create_property(key=constant.AIRLINE_LEGAL_NAME, value=airline.legal_name),
            create_property(key=constant.AIRLINE_IDENTIFIER, value=airline.identifier),
            create_property(key=constant.AIRLINE_LOCATION, value=airline.hq_location),
        ]

        # The Airline Twin's Properties will be the same as the Twin Models',
        # except the ones we defined above and some other exceptions.
        for twin_model_property in twin_model_properties:
            if twin_model_property.key in [
                constant.TYPE,
                constant.LABEL,
                constant.DEFINES,
            ]:
                continue

            twin_properties.append(twin_model_property)

        # Generate a new Twin Registered Identity for the Airline Twin
        airline_twin_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name=airline.name
            )
        )

        airline_twin_id = airline_twin_identity.did

        try:
            with self._refresh_token_lock:
                self._iotics_api.upsert_twin(
                    twin_did=airline_twin_id, properties=twin_properties
                )
        except grpc.RpcError as ex:
            if not is_token_expired(exception=ex, operation="create_twin_from_model"):
                sys.exit(1)

        log.info("%s Airline Twin created: %s", airline.name, airline_twin_id)

        return airline_twin_id

    def _get_current_country(self, lat: float, lon: float) -> Country:
        current_country = Country()
        for country in self._countries_list:
            if (
                country.lat_min <= lat <= country.lat_max
                and country.lon_min <= lon <= country.lon_max
            ):
                current_country = country
                break

        return current_country

    def _evaluate_action(
        self,
        airline: Airline,
        flight_twin_label: str,
        flight_arrival_airport: str,
        new_lat: float,
        new_lon: float,
        current_country: Country,
    ) -> int:
        flight_arrived = False

        for airport in constant.AIRPORT_COORDINATES:
            airport_coords = airport.get("coords")
            airport_name = airport.get("name")
            if (
                airport_coords.get("lat") == new_lat
                and airport_coords.get("lon") == new_lon
                and flight_arrival_airport == airport_name
            ):
                flight_arrived = True

        # The flight is within the HQ's borders
        if current_country.name == airline.hq_location or flight_arrived:
            action = 1
        else:  # The flight is outside the HQ's borders
            log.debug("%s outside HQ's border", flight_twin_label)
            action = 2

        return action, current_country

    def _create_twin_shadow(
        self, airline: Airline, flight_twin, current_country: Country, shadow_twin_label
    ) -> str:
        flight_twin_did = flight_twin.twinId.id
        flight_twin_properties = flight_twin.properties

        shadow_twin_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name=hash(flight_twin_did)
            )
        )

        shadow_twin_id = shadow_twin_identity.did
        restricted_properties = [
            constant.HOST_METADATA_ALLOW_LIST,
            constant.LABEL,
        ]

        for restricted_country, properties in airline.restricted_properties.items():
            if restricted_country.name == current_country.name:
                restricted_properties.extend(properties)

        shadow_twin_properties = [
            flight_twin_property
            for flight_twin_property in flight_twin_properties
            if flight_twin_property.key not in restricted_properties
        ]

        shadow_twin_properties.append(
            create_property(key=constant.LABEL, value=shadow_twin_label),
            # create_property(
            #     key=constant.HOST_METADATA_ALLOW_LIST,
            #     value=current_country.host_id,
            #     is_uri=True,
            # ),
        )

        shadow_feeds = [
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
                    twin_did=shadow_twin_id,
                    properties=shadow_twin_properties,
                    feeds=shadow_feeds,
                )
        except grpc.RpcError as ex:
            if not is_token_expired(exception=ex, operation="upsert_twin_shadow"):
                sys.exit(1)

        return shadow_twin_id

    def _update_twin_shadow(self, shadow_twin_id: str):
        try:
            with self._refresh_token_lock:
                self._iotics_api.update_twin(twin_did=shadow_twin_id)
        except grpc.RpcError as ex:
            if not is_token_expired(exception=ex, operation="update_twin_shadow"):
                sys.exit(1)

    def _follow_flight_twins(self, airline: Airline, flight_twins):
        for flight_twin in flight_twins:
            flight_twin_did = flight_twin.twinId.id
            flight_twin_label = self._get_twin_property(
                twin_properties=flight_twin.properties, key=constant.LABEL
            )
            if "Shadow" in flight_twin_label.langLiteralValue.value:
                continue

            # Check if the flight Twin is already being followed
            if not self._flights_shadow.get(flight_twin_did):
                log.info(
                    "Starting to follow Flight Twin %s: %s",
                    flight_twin_label.langLiteralValue.value,
                    flight_twin_did,
                )

                Thread(
                    target=self._receive_feed_data, args=[airline, flight_twin]
                ).start()
            else:
                log.info("Flight Twin %s is already being followed", flight_twin_did)

    def _search_flight_twins(self, airline_twin_id: str):
        log.info("Searching for Flight Twins...")

        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.FLIGHT_ONTOLOGY, is_uri=True
                ),
                create_property(
                    key=constant.FLIGHT_PROVIDER, value=airline_twin_id, is_uri=True
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

        return twins_found_list

    @staticmethod
    def _get_twin_property(twin_properties, key) -> str:
        for twin_property in twin_properties:
            if twin_property.key == key:
                return twin_property

        return None

    def _process_flight_data(self, airline, flight_twin, flight_data):
        new_lat = flight_data.get(constant.FLIGHT_FEED_LABEL_LAT)
        new_lon = flight_data.get(constant.FLIGHT_FEED_LABEL_LON)
        current_country = self._get_current_country(lat=new_lat, lon=new_lon)
        flight_label_property = self._get_twin_property(
            twin_properties=flight_twin.properties, key=constant.LABEL
        )
        flight_label_str = flight_label_property.langLiteralValue.value
        flight_arrival_airport_property = self._get_twin_property(
            twin_properties=flight_twin.properties,
            key=constant.FLIGHT_ARRIVAL_AIRPORT,
        )
        flight_arrival_airport_str = (
            flight_arrival_airport_property.stringLiteralValue.value
        )
        flight_twin_did = flight_twin.twinId.id

        log.debug(
            "New location received from %s: (%.4f, %.4f). Current Country: %s",
            flight_label_str,
            new_lat,
            new_lon,
            current_country.name,
        )
        shadow_twin_label = f"{flight_label_str.langLiteralValue.value} Shadow"

        action = self._evaluate_action(
            airline,
            flight_label_str,
            flight_arrival_airport_str,
            new_lat,
            new_lon,
            current_country,
        )

        # delete Flight Shadow (if existing)
        if action == 1:
            shadow_twin_id: str = self._flights_shadow.pop(flight_twin_did, None)
            if shadow_twin_id:
                self._iotics_api.delete_twin(twin_did=shadow_twin_id)
                log.info("%s Twin deleted: %s", shadow_twin_label, shadow_twin_id)

        # update/upsert Flight Shadow
        elif action == 2:
            shadow_twin_id = self._flights_shadow.get(flight_twin_did)
            if not shadow_twin_id:
                shadow_twin_id = self._create_twin_shadow(
                    airline,
                    flight_twin,
                    current_country,
                    shadow_twin_label,
                )
                self._flights_shadow.update({flight_twin_did: shadow_twin_id})
                log.info("%s Twin created: %s", shadow_twin_label, shadow_twin_id)
            else:
                self._update_twin_shadow(shadow_twin_id, new_lat, new_lon)
                log.info("%s Twin updated", shadow_twin_label)

            try:
                with self._refresh_token_lock:
                    self._iotics_api.share_feed_data(
                        twin_did=shadow_twin_id,
                        feed_id=constant.FLIGHT_FEED_ID,
                        data={
                            constant.FLIGHT_FEED_LABEL_LAT: new_lat,
                            constant.FLIGHT_FEED_LABEL_LON: new_lon,
                        },
                    )
                    log.debug(
                        "Shared feed data (%.4f, %.4f) from %s",
                        new_lat,
                        new_lon,
                        flight_label_str,
                    )
            except grpc.RpcError as ex:
                if not is_token_expired(exception=ex, operation="receive_feed_data"):
                    sys.exit(1)

    def _receive_feed_data(self, airline: Airline, flight_twin):
        log.debug("Waiting for Flight's Feed data...")

        flight_twin_did = flight_twin.twinId.id

        while True:
            try:
                with self._refresh_token_lock:
                    feed_listener = self._iotics_api.fetch_interests(
                        follower_twin_did=airline.airline_twin_id,
                        followed_twin_did=flight_twin_did,
                        followed_feed_id=constant.FLIGHT_FEED_ID,
                        fetch_last_stored=False,
                    )
            except grpc.RpcError as ex:
                if not is_token_expired(exception=ex, operation="fetch_interests"):
                    sys.exit(1)
                else:
                    continue

            try:
                for latest_feed_data in feed_listener:
                    flight_data = json.loads(latest_feed_data.payload.feedData.data)
                    self._process_flight_data(airline, flight_twin, flight_data)
            except grpc.RpcError as ex:
                if not is_token_expired(exception=ex, operation="feed_listener"):
                    break

    def create_new_airline(
        self,
        name: str,
        legal_name: str,
        identifier: str,
        hq_country: Country,
        restricted_properties: dict,
    ):
        airline = Airline(
            name, legal_name, identifier, hq_country, restricted_properties
        )
        airline_twin_id = self._create_twin_from_model(airline)
        airline.twin_id = airline_twin_id
        self._airlines_list.append(airline)

    def start(self):
        while True:
            for airline in self._airlines_list:
                airline_flight_twins = self._search_flight_twins(
                    airline_twin_id=airline.airline_twin_id
                )
                self._follow_flight_twins(airline, airline_flight_twins)

            sleep(constant.SEARCH_NEW_FLIGHTS_SLEEP_TIME)
