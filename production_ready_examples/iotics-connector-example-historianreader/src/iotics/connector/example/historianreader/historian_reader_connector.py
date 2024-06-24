import logging
import os
from threading import Lock, Thread
from time import sleep
from typing import List

import constants as constant
import grpc
from data_processor import DataProcessor
from identity import Identity
from iotics.lib.grpc.helpers import (
    create_input_with_meta,
    create_property,
    create_value,
)
from iotics.lib.grpc.iotics_api import IoticsApi
from twin_structure import TwinStructure
from utilities import (
    expected_grpc_exception,
    get_host_endpoints,
    retry_on_exception,
    search_twins,
)

log = logging.getLogger(__name__)


class HistorianReaderConnector:
    def __init__(self, data_processor: DataProcessor):
        """Constructor of a Historian Reader Connector object.

        Args:
            data_processor (DataProcessor): object simulating a data processor engine.
        """

        self._data_processor: DataProcessor = data_processor
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._threads_list: List[Thread] = None
        self._historian_reader_twin_did: str = None

        self._initialise()

    def _initialise(self):
        """Initialise all the variables of this class. It also starts
        an auto refresh token Thread so the IOTICS token is automatically
        regenerated when it expires.
        """

        log.debug("Initialising Historian Reader Connector...")
        endpoints = get_host_endpoints(host_url=os.getenv("HISTORIANREADER_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("HISTORIANREADER_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("HISTORIANREADER_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._refresh_token_lock = Lock()
        self._threads_list = []

        # Start auto-refreshing token Thread in the background
        Thread(
            target=self._iotics_identity.auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

    def _setup_twin_structure(self) -> TwinStructure:
        """Define the Twin structure in terms of Twin's metadata.

        Returns:
            TwinStructure: an object representing the structure of the Twin
        """

        twin_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.REQUEST, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Historian Reader", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="Read data from Database",
                language="en",
            ),
            create_property(
                key=constant.FULL_NAME, value=constant.PROPERTY_VALUE_CREATED_BY_NAME
            ),
            create_property(
                key=constant.ORGANISATION, value=constant.ORGANISATION_VALUE
            ),
            create_property(
                key=constant.EMAIL_ADDRESS, value=constant.EMAIL_ADDRESS_VALUE
            ),
            create_property(
                key=constant.PROPERTY_KEY_CREATED_BY,
                value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
            ),
        ]

        credentials_info_input_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.VERIFICATION, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL,
                value="DB credentials Info",
                language="en",
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="DB credentials Info to access the Database",
                language="en",
            ),
        ]
        credentials_info_input_values = [
            create_value(
                label=constant.DB_NAME_INPUT_VALUE,
                data_type="string",
                comment="Name of the DB",
            ),
            create_value(
                label=constant.DB_USERNAME_INPUT_VALUE,
                data_type="string",
                comment="Username used to access the DB",
            ),
            create_value(
                label=constant.DB_PASSWORD_INPUT_VALUE,
                data_type="string",
                comment="Password used to access the DB",
            ),
        ]

        inputs_list = [
            create_input_with_meta(
                input_id=constant.DB_ACCESS_INFO_INPUT_ID,
                properties=credentials_info_input_properties,
                values=credentials_info_input_values,
            )
        ]

        twin_structure = TwinStructure(
            properties=twin_properties, inputs_list=inputs_list
        )

        return twin_structure

    def _create_twin(self, twin_structure: TwinStructure):
        """Create the Historian Reader Twin given a Twin Structure.

        Args:
            twin_structure (TwinStructure): Structure of the Data Reader Twin to create.
        """

        log.info("Creating Historian Reader Twin...")

        twin_identity = self._iotics_identity.create_twin_with_control_delegation(
            twin_key_name="HistorianReaderTwin"
        )
        twin_did = twin_identity.did
        log.debug("Generated new Twin DID: %s", twin_did)

        retry_on_exception(
            self._iotics_api.upsert_twin,
            "upsert_twin",
            self._refresh_token_lock,
            twin_did=twin_did,
            properties=twin_structure.properties,
            inputs=twin_structure.inputs_list,
        )

        log.info("Created Historian Reader Twin with DID: %s", twin_did)

        self._historian_reader_twin_did = twin_did

    def _process_message(self, new_input_message):
        log.debug("Processing message...")
        received_data, _ = self._data_processor.input_data_unpack(new_input_message)

        db_name = received_data.get(constant.DB_NAME_INPUT_VALUE)
        db_username = received_data.get(constant.DB_USERNAME_INPUT_VALUE)
        db_password = received_data.get(constant.DB_PASSWORD_INPUT_VALUE)

        log.info("Accessing DB with credentials received...")

        is_db_initialised = self._data_processor.initialise_db_reader(
            db_name=db_name, db_username=db_username, db_password=db_password
        )

        if is_db_initialised:
            self._data_processor.print_all_data_from_db()
        else:
            log.info("DB not initialised correctly")

    def _receive_input_messages(self, input_id: str):
        log.info("Waiting for DB Credentials...")

        unexpected_exception_counter: int = 0

        while True:
            log.debug("Generating a new input_listener...")

            input_listener = retry_on_exception(
                self._iotics_api.receive_input_messages,
                "receive_input_messages",
                self._refresh_token_lock,
                twin_did=self._historian_reader_twin_did,
                input_id=input_id,
            )

            try:
                for new_input_message in input_listener:
                    # Print Input Message received on screen
                    self._data_processor.print_input_message_on_screen(
                        receiver_twin_did=self._historian_reader_twin_did,
                        receiver_input_id=input_id,
                        input_message=new_input_message,
                    )

                    self._process_message(new_input_message)
            except grpc.RpcError as grpc_ex:
                # Any time the token expires, an expected gRPC exception is raised
                # and a new 'input_listener' object needs to be generated.
                if not expected_grpc_exception(
                    exception=grpc_ex, operation="input_listener"
                ):
                    unexpected_exception_counter += 1
            except Exception as gen_ex:
                log.exception("General exception in 'input_listener': %s", gen_ex)
                unexpected_exception_counter += 1

            if unexpected_exception_counter > constant.RETRYING_ATTEMPTS:
                break

        log.debug("Exiting thread...")

    def _search_data_bypass_twins(self):
        """Search for the Data Bypass Twins.

        Returns:
            twins_found_list: list of Twins found by the Search operation.
        """

        log.info("Searching for Data Bypass Twins...")
        search_criteria = self._iotics_api.get_search_payload(
            properties=[
                create_property(
                    key=constant.PROPERTY_KEY_TYPE,
                    value=constant.DATA_ACCESS,
                    is_uri=True,
                ),
                create_property(
                    key=constant.PROPERTY_KEY_CREATED_BY,
                    value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
                ),
            ],
            response_type="FULL",
        )

        twins_found_list = search_twins(
            search_criteria, self._refresh_token_lock, self._iotics_api, True
        )

        log.info("Found %d Twins based on the search criteria", len(twins_found_list))

        return twins_found_list

    def _send_db_access_request_messages(self, data_bypass_twins_list):
        for data_bypass_twin in data_bypass_twins_list:
            data_bypass_twin_id = data_bypass_twin.twinId.id
            message_to_send = {
                constant.SENDER_TWIN_ID_VALUE: self._historian_reader_twin_did
            }

            self._iotics_api.send_input_message(
                sender_twin_did=self._historian_reader_twin_did,
                receiver_twin_did=data_bypass_twin_id,
                input_id=constant.VERIFICATION_INFO_INPUT_ID,
                message=message_to_send,
            )
            log.debug(
                "Sent Input Message %s to %s", message_to_send, data_bypass_twin_id
            )
            log.info("DB access request sent")

    def _start_receiving_input_messages(self, twin_structure):
        for input in twin_structure.inputs_list:
            input_thread = Thread(target=self._receive_input_messages, args=[input.id])
            input_thread.start()
            self._threads_list.append(input_thread)

    def start(self):
        twin_structure = self._setup_twin_structure()
        self._create_twin(twin_structure)
        self._start_receiving_input_messages(twin_structure)
        data_bypass_twins_list = self._search_data_bypass_twins()
        self._send_db_access_request_messages(data_bypass_twins_list)
