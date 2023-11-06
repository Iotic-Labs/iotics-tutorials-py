import json
import logging
import os
import sys
from threading import Thread
from time import sleep

import constants as constant
import grpc
from identity import Identity
from iotics.lib.grpc.helpers import create_property, create_location
from iotics.lib.grpc.iotics_api import IoticsApi
from utilities import auto_refresh_token, get_host_endpoints

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class AirlineConnector:
    def __init__(
        self,
        airline_name: str,
        legal_name: str,
        airline_identifier: str,
        airline_hq_location: str,
    ):
        self._airline_name: str = airline_name
        self._legal_name: str = legal_name
        self._airline_identifier: str = airline_identifier
        self._airline_hq_location: str = airline_hq_location
        self._iotics_api: IoticsApi = None
        self._iotics_identity: Identity = None
        self._airline_twin_did: str = None
        self._flight_shadow_dict: dict = None

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
        self._flight_shadow_dict = {}

        # Auto-generate a new token when it expires
        Thread(
            target=auto_refresh_token,
            args=[self._iotics_identity, self._iotics_api],
            daemon=True,
        ).start()

    def _create_twin_model(self):
        logging.info("Creating Twin Model...")
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

        # Upsert Twin
        self._iotics_api.upsert_twin(
            twin_did=airline_twin_model_identity.did,
            properties=twin_model_properties,
        )

        logging.info(
            "%s Twin created: %s",
            constant.AIRLINE_TWIN_MODEL_LABEL,
            airline_twin_model_identity.did,
        )

    def _search_airline_twin_model(self):
        logging.info("Searching for Airline Twin Model ...")

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

        twins_found_list = []
        # Keep searching until the Twin Model is found.
        # The latter could be created after this search operation is executed.
        attempts: int = 0
        while True:
            for response in self._iotics_api.search_iter(
                client_app_id=self._airline_name, payload=search_criteria
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

    def _create_airline_twin(self, airline_twin_model):
        logging.info("Creating Airline Twin for %s ...", self._airline_name)

        twin_model_id = airline_twin_model.twinId.id
        twin_model_properties = airline_twin_model.properties

        twin_properties = [
            create_property(
                key=constant.TWIN_FROM_MODEL, value=twin_model_id, is_uri=True
            ),
            create_property(
                key=constant.LABEL, value=self._airline_name, language="en"
            ),
            create_property(
                key=constant.TYPE, value=constant.AIRLINE_ONTOLOGY, is_uri=True
            ),
            create_property(key=constant.AIRLINE_LEGAL_NAME, value=self._legal_name),
            create_property(
                key=constant.AIRLINE_IDENTIFIER, value=self._airline_identifier
            ),
            create_property(
                key=constant.AIRLINE_LOCATION, value=self._airline_hq_location
            ),
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
                twin_key_name=self._airline_name
            )
        )

        self._airline_twin_did = airline_twin_identity.did

        # Upsert Twin
        self._iotics_api.upsert_twin(
            twin_did=self._airline_twin_did,
            properties=twin_properties,
        )

        logging.info(
            "%s Airline Twin created: %s", self._airline_name, self._airline_twin_did
        )

    def _get_country(self, lat: float, lon: float):
        # Return country from constants based on lat and lon
        country = ""

        return country

    def _evaluate_action(
        self, flight_twin_did: str, new_lat: float, new_lon: float
    ) -> int:
        logging.info("New location received from Flight Twin %s", flight_twin_did)

        flight_shadow: FlightShadow = self._flight_shadow_dict.get(flight_twin_did)

        if not flight_shadow:
            return 1

        elif self._get_country(lat=new_lat, lon=new_lon) == self._airline_hq_location:
            # The flight is within the HQ's borders
            return 3

        else:
            # The flight is outside the HQ's borders
            return 2

    def _manage_flight_twin(self, flight_twin_description):
        flight_twin_did = flight_twin_description.twinId.id

        if self._flight_shadow_dict.get(flight_twin_did):
            logging.info("Flight Twin %s already managed", flight_twin_did)
        else:
            Thread(
                target=self._receive_feed_data,
                args=[self._iotics_identity, self._iotics_api, flight_twin_description],
            ).start()

    def _search_flight_twins(self):
        logging.info("Searching for Flight Twins ...")

        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.TYPE, value=constant.FLIGHT_ONTOLOGY, is_uri=True
                ),
                create_property(
                    key=constant.FLIGHT_PROVIDER,
                    value=self._airline_twin_did,
                    is_uri=True,
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

        while True:
            try:
                for response in self._iotics_api.search_iter(
                    client_app_id=self._airline_name, payload=search_criteria
                ):
                    twins = response.payload.twins
                    twins_found_list.extend(twins)

                for flight_twin in twins_found_list:
                    self._manage_flight_twin(flight_twin_description=flight_twin)
            except KeyboardInterrupt:
                logging.info("Exiting Airline Connector")
                break

    def _receive_feed_data(
        self, iotics_identity: Identity, iotics_api: IoticsApi, flight_twin_description
    ):
        logging.info("Waiting for Feed data ...")

        flight_twin_did = flight_twin_description.twinId.id

        while True:
            feed_listener = iotics_api.fetch_interests(
                follower_twin_did=self._airline_twin_did,
                followed_twin_did=flight_twin_did,
                followed_feed_id=constant.FLIGH_FEED_ID,
            )

            try:
                for latest_feed_data in feed_listener:
                    new_location: dict = json.loads(
                        latest_feed_data.payload.feedData.data
                    )

                    new_lat = new_location.get(constant.FLIGHT_FEED_LABEL_LAT)
                    new_lon = new_location.get(constant.FLIGHT_FEED_LABEL_LON)

                    action = self._evaluate_action(
                        flight_twin_did=flight_twin_did,
                        new_lat=new_lat,
                        new_lon=new_lon,
                    )

                    if action == 1:  # create new Shadow
                        flight_shadow = FlightShadow(
                            iotics_identity=iotics_identity, iotics_api=iotics_api
                        )
                        self._flight_shadow_dict.update(
                            {flight_twin_did: flight_shadow}
                        )
                    elif action == 2:  # update existing shadow
                        flight_shadow: FlightShadow = self._flight_shadow_dict.get(
                            flight_twin_did
                        )
                        flight_shadow.update_twin()
                    elif action == 3:  # delete existing shadow
                        flight_shadow: FlightShadow = self._flight_shadow_dict.pop(
                            flight_twin_did
                        )
                        flight_shadow.delete_twin()

            except KeyboardInterrupt:
                logging.debug("Keyboard Interrupt. Exiting Thread")
                break
            except grpc._channel._MultiThreadedRendezvous as ex:
                if ex.code() == grpc.StatusCode.UNAUTHENTICATED:
                    logging.debug("Generating new 'input_listener'")
                else:
                    logging.exception(
                        "Raised an exception in 'get_input_listener': %s", ex
                    )
                    break

            sleep(0.25)

    def start(self):
        airline_twin_model = self._search_airline_twin_model()
        self._create_airline_twin(airline_twin_model=airline_twin_model)
        self._search_flight_twins()


class FlightShadow:
    def __init__(self, iotics_identity: Identity, iotics_api: IoticsApi):
        self._iotics_api: IoticsApi = iotics_identity
        self._iotics_identity: Identity = iotics_api
        self._shadow_twin_did: str = None
        self._country: str = None

    @property
    def country(self) -> str:
        return self._country

    def update_twin(self, new_lat: float, new_lon: float):
        # Update selective sharing permissions
        updated_sharing_permissions = [
            create_property(key=constant.HOST_ALLOW_LIST, value="host_id", is_uri=True),
            create_property(
                key=constant.HOST_METADATA_ALLOW_LIST, value="host_id", is_uri=True
            ),
        ]

        self._iotics_api.update_twin(
            twin_did=self._shadow_twin_did,
            location=create_location(lat=new_lat, lon=new_lon),
            props_added=updated_sharing_permissions,
            props_keys_deleted=[
                twin_prop.key for twin_prop in updated_sharing_permissions
            ],
        )

    def delete_twin(self):
        self._iotics_api.delete_twin(twin_did=self._shadow_twin_did)
