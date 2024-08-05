import logging
import os
from datetime import datetime
from threading import Event, Lock, Thread
from time import sleep

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
        self._historian_reader_twin_did: str = None
        self._last_db_access_datetime: datetime = None
        self._db_initialised_event: Event = None

        self._initialise()

    def _initialise(self):
        """Initialise all the variables of this class. It also starts
        an auto refresh token Thread so the IOTICS token is automatically
        regenerated when it expires.
        """

        log.debug("Initialising Historian Reader Connector...")
        endpoints = get_host_endpoints(host_url=os.getenv("HISTORIAN_READER_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("HISTORIAN_READER_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("HISTORIAN_READER_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._db_initialised_event = Event()
        self._refresh_token_lock = Lock()

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

        # Twin Properties definition
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

        # Input Properties definition
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
        # Input values definition
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
            twin_structure (TwinStructure): Structure of the Historian Reader Twin to create.
        """

        log.info("Creating Historian Reader Twin...")

        twin_identity = self._iotics_identity.create_twin_with_control_delegation(
            twin_key_name="HistorianReaderTwin"
        )
        twin_did = twin_identity.did
        log.debug("Generated new Twin DID: %s", twin_did)

        retry_on_exception(
            grpc_operation=self._iotics_api.upsert_twin,
            function_name="upsert_twin",
            refresh_token_lock=self._refresh_token_lock,
            twin_did=twin_did,
            properties=twin_structure.properties,
            inputs=twin_structure.inputs_list,
        )

        log.info("Created Historian Reader Twin with DID: %s", twin_did)

        self._historian_reader_twin_did = twin_did

    def _process_message(self, new_input_message):
        """Retrieve credentials to access the DB from the Input message received.
        Use the credentials to extract all data from the DB and print it on screen.

        Args:
            new_input_message: input message received that includes the credentials
                to access the DB.
        """

        log.debug("Processing Input message...")
        received_data, occurred_at_timestamp = self._data_processor.unpack_input_data(
            new_input_message
        )

        # Get the DB credentials from the Input message
        db_name = received_data.get(constant.DB_NAME_INPUT_VALUE)
        db_username = received_data.get(constant.DB_USERNAME_INPUT_VALUE)
        db_password = received_data.get(constant.DB_PASSWORD_INPUT_VALUE)

        log.info("Accessing DB with credentials received...")

        # Now the DB can be initialised
        is_db_initialised = self._data_processor.initialise_db_reader(
            db_name=db_name, db_username=db_username, db_password=db_password
        )
        if is_db_initialised:
            self._db_initialised_event.set()

    def _receive_input_messages(self):
        """Wait for Input messages sent to the historian reader Twin's Input.
        Upon receiving a message, process it accordingly.
        """

        log.info("Waiting for DB Credentials...")

        unexpected_exception_counter: int = 0

        while True:
            log.debug("Generating a new input_listener...")

            input_listener = retry_on_exception(
                grpc_operation=self._iotics_api.receive_input_messages,
                function_name="receive_input_messages",
                refresh_token_lock=self._refresh_token_lock,
                twin_did=self._historian_reader_twin_did,
                input_id=constant.DB_ACCESS_INFO_INPUT_ID,
            )

            try:
                for new_input_message in input_listener:
                    # Print Input Message received on screen
                    self._data_processor.print_input_message_on_screen(
                        receiver_twin_did=self._historian_reader_twin_did,
                        receiver_input_id=constant.DB_ACCESS_INFO_INPUT_ID,
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
            search_criteria=search_criteria,
            refresh_token_lock=self._refresh_token_lock,
            iotics_api=self._iotics_api,
        )

        log.info("Found %d Twins based on the search criteria", len(twins_found_list))

        return twins_found_list

    def _send_db_access_request(self, data_bypass_twins_list):
        """Sends a DB access request (i.e.: Input message) to
        the Data Bypass Twin(s) found by the search twin operation.
        Repeats the operation if the DB creds are not received within a timeout.

        Args:
            data_bypass_twins_list: list of data bypass Twins found
                by the search twin operation.
        """

        while not self._db_initialised_event.is_set():
            for data_bypass_twin in data_bypass_twins_list:
                data_bypass_twin_id = data_bypass_twin.twinId.id

                # Prepare Input message to send by including
                # the historian reader Twin ID.
                message_to_send = {
                    constant.SENDER_TWIN_ID_VALUE: self._historian_reader_twin_did
                }

                retry_on_exception(
                    grpc_operation=self._iotics_api.send_input_message,
                    function_name="send_input_message",
                    refresh_token_lock=self._refresh_token_lock,
                    sender_twin_did=self._historian_reader_twin_did,
                    receiver_twin_did=data_bypass_twin_id,
                    input_id=constant.VERIFICATION_INFO_INPUT_ID,
                    message=message_to_send,
                )

                log.debug(
                    "Sent Input Message %s to %s", message_to_send, data_bypass_twin_id
                )
                log.info("DB access request sent")

            sleep(constant.ACCESS_DB_PERIOD)

            if self._db_initialised_event.is_set():
                log.info("DB initialised")
                break
            else:
                log.info("Sending a new DB request...")

    def _wait_for_db_credentials(self):
        """Starts a thread to asynchronously wait for input messages."""

        input_thread = Thread(target=self._receive_input_messages)
        input_thread.start()

    def _periodically_access_db(self):
        """Creates an infinite loop to periodically access the DB and print the data."""

        while True:
            datetime_now = datetime.now()

            # Get all data from the DB if this is the first access
            if not self._last_db_access_datetime:
                log.info("Printing ALL data from DB...")
                self._data_processor.print_all_data_from_db()

            # Get the new data from the DB if this is not the first access
            else:
                log.info(
                    "Printing data from %s to %s...",
                    self._last_db_access_datetime.strftime(constant.DATETIME_FORMAT),
                    datetime_now.strftime(constant.DATETIME_FORMAT),
                )
                self._data_processor.print_datetime_range_data_from_db(
                    start_datetime=self._last_db_access_datetime,
                    end_datetime=datetime_now,
                )

            self._last_db_access_datetime = datetime_now

            log.info(
                "Waiting for %ds before accessing the DB again...",
                constant.ACCESS_DB_PERIOD,
            )
            sleep(constant.ACCESS_DB_PERIOD)

    def start(self):
        """Create a Historian Reader Twin. Then, search for the Data Bypass Twin and
        send a database access request to it via the Historian Reader Twin.
        Wait for the credentials to access the database.
        """

        twin_structure = self._setup_twin_structure()
        self._create_twin(twin_structure)
        self._wait_for_db_credentials()
        data_bypass_twins_list = self._search_data_bypass_twins()
        self._send_db_access_request(data_bypass_twins_list)
        self._periodically_access_db()
