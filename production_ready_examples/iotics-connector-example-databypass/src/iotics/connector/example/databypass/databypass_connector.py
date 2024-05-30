import logging
import os
from threading import Lock, Thread
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
from utilities import expected_grpc_exception, get_host_endpoints, retry_on_exception

log = logging.getLogger(__name__)


class DataBypassConnector:
    def __init__(self, data_processor: DataProcessor):
        """Constructor of a Follower Connector object.

        Args:
            data_processor (DataProcessor): object simulating a data processor engine.
        """

        self._data_processor: DataProcessor = data_processor
        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._threads_list: List[Thread] = None
        self._data_bypass_twin_did: str = None

        self._initialise()

    def _initialise(self):
        """Initialise all the variables of this class. It also starts
        an auto refresh token Thread so the IOTICS token is automatically
        regenerated when it expires.
        """

        log.debug("Initialising DataBypass Connector...")
        endpoints = get_host_endpoints(host_url=os.getenv("DATABYPASS_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("DATABYPASS_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("DATABYPASS_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._data_processor.initialise_db_writer(
            db_name=os.getenv("DB_NAME"),
            db_username=os.getenv("DB_USERNAME"),
            db_password=os.getenv("POSTGRES_PASSWORD"),
        )

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

        # Twin Properties definition
        twin_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.DATA_ACCESS, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL,
                value="Data Bypass for IOTICS tutorials",
                language="en",
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="Twin used to provide access to data out-of-band",
                language="en",
            ),
            create_property(
                key=constant.PROPERTY_KEY_CREATED_BY,
                value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
            ),
        ]

        # Input Properties definition
        requester_input_properties = [
            create_property(
                key=constant.PROPERTY_KEY_TYPE, value=constant.REQUEST, is_uri=True
            ),
            create_property(
                key=constant.PROPERTY_KEY_LABEL, value="Requester Info", language="en"
            ),
            create_property(
                key=constant.PROPERTY_KEY_COMMENT,
                value="Requester Info of an entity who wants to access the Data Archive",
                language="en",
            ),
        ]
        # Input values definition
        requester_input_values = [
            create_value(
                label=constant.SENDER_TWIN_ID_VALUE,
                data_type="string",
                comment="Twin ID that requested access the Data Archive",
            ),
        ]

        inputs_list = [
            create_input_with_meta(
                input_id=constant.VERIFICATION_INFO_INPUT_ID,
                properties=requester_input_properties,
                values=requester_input_values,
            )
        ]

        twin_structure = TwinStructure(
            properties=twin_properties, inputs_list=inputs_list
        )

        return twin_structure

    def _create_twin(self, twin_structure: TwinStructure):
        """Create the Twin Follower given a Twin Structure.

        Args:
            twin_structure (TwinStructure): Structure of the Twin Follower to create.
        """

        log.info("Creating Data Bypass Twin...")

        twin_identity = self._iotics_identity.create_twin_with_control_delegation(
            twin_key_name="DataBypassTwin"
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

        log.info("Created Data Bypass Twin with DID: %s", twin_did)

        self._data_bypass_twin_did = twin_did

    def _grant_db_access(self, twin_requester_id: str, full_name: str):
        """Generate a 'username' and 'password' to send to the Twin requester
        so they can be used to access the DB.

        Args:
            twin_requester_id (str): the Twin DID asking for DB access.
            full_name (str): the Twin requester's full name,
                used to generate the credentials.
        """

        username, password = self._data_processor.generate_db_credentials(
            full_name=full_name
        )

        # Compose Input message to send to the Twin requester
        message_to_send = {
            constant.DB_NAME_INPUT_VALUE: os.getenv("DB_NAME"),
            constant.DB_USERNAME_INPUT_VALUE: username,
            constant.DB_PASSWORD_INPUT_VALUE: password,
        }

        # Send Input message with the credentials to access the DB
        self._iotics_api.send_input_message(
            sender_twin_did=self._data_bypass_twin_did,
            receiver_twin_did=twin_requester_id,
            input_id=constant.DB_ACCESS_INFO_INPUT_ID,
            message=message_to_send,
        )

        log.info("DB credentials sent")

    def _process_request(self, new_input_message):
        """Process the input message, expected to be a DB request.
        Retrieve the Sender Twin DID from the input message to perform a Describe Twin operation.
        Obtain the necessary information to determine if the requester should be granted DB access.
        If the 'organisation' is permitted, then grant DB access. If not, ignore the Input message.

        Args:
            new_input_message: Input message received, expected to be a DB request.
        """

        log.debug("Processing request...")
        received_data, occurred_at_timestamp = self._data_processor.unpack_input_data(
            new_input_message
        )

        log.info("Received new DB request: %s", received_data)

        # Get the Twin Requester DID from the Input message
        twin_requester_id = received_data.get(constant.SENDER_TWIN_ID_VALUE)

        if not twin_requester_id:
            log.info(
                "Twin Requester ID missing from Input message received. Ignoring message"
            )
            return

        # Describe Twin Requester to get the necessary info
        # to determine if the requester should be granted DB access
        log.info("Describing Twin %s...", twin_requester_id)
        twin_description = self._iotics_api.describe_twin(twin_did=twin_requester_id)
        twin_receiver_properties = twin_description.payload.result.properties

        organisation = full_name = email_address = None
        for twin_property in twin_receiver_properties:
            if twin_property.key == constant.ORGANISATION:
                organisation = twin_property.stringLiteralValue.value
            elif twin_property.key == constant.FULL_NAME:
                full_name = twin_property.stringLiteralValue.value
            elif twin_property.key == constant.EMAIL_ADDRESS:
                email_address = twin_property.stringLiteralValue.value

        # For this example, only the 'organisation' field is checked
        if not organisation:
            log.info("Organisation unknown. Ignoring request")
            return

        log.info(
            "DB request from %s at %s email %s", full_name, organisation, email_address
        )

        # The Twin requester's organisation is allowed. Grant DB access
        if organisation in constant.ORGANISATIONS_ALLOWED_LIST:
            log.debug("Organisation '%s' allowed to get DB access", organisation)

            self._grant_db_access(
                twin_requester_id=twin_requester_id, full_name=full_name
            )
        # The Twin requester's organisation is not allowed. Ignore message
        else:
            log.info(
                "Organisation '%s' NOT allowed to receive DB access. Ignoring message",
                organisation,
            )

    def _wait_for_input_messages(self):
        """Wait for Input messages sent to the data bypass Twin's Input.
        Upon receiving a message, process it accordingly.
        """

        log.info("Waiting for DB requests...")

        unexpected_exception_counter: int = 0

        while True:
            log.debug("Generating a new input_listener...")

            # Generate a new Input listener
            input_listener = retry_on_exception(
                grpc_operation=self._iotics_api.receive_input_messages,
                function_name="receive_input_messages",
                refresh_token_lock=self._refresh_token_lock,
                twin_did=self._data_bypass_twin_did,
                input_id=constant.VERIFICATION_INFO_INPUT_ID,
            )

            try:
                # Wait to receive Input messages
                for new_input_message in input_listener:
                    self._process_request(new_input_message)
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

    def start(self):
        """Create a Data Bypass Twin which waits for DB access requests
        via Input Messages."""

        twin_structure = self._setup_twin_structure()
        self._create_twin(twin_structure)
        self._wait_for_input_messages()
