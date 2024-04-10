import logging
import os
from datetime import datetime, timedelta
from threading import Lock, Thread, Timer
from threading import enumerate as enumerate_threads
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
from pip_data import PIPData
from twin_structure import TwinStructure
from utilities import (
    auto_refresh_token,
    get_host_endpoints,
    retry_on_exception,
    search_twins,
)

log = logging.getLogger(__name__)


class VesselMovementConnector:
    """This Class implements a Publisher Connector responsible for creating Vessel Twins
    and sharing event-based information about arrivals and departures to/from the
    Portsmouth International Port (PIP).
    Each Vessel Twin comprises two Feeds: one for arrival and the other for departure information,
    both sharing data in an event-based manner based on the Vessel's ATA and ATD respectively.
    """

    def __init__(self, pip_data: PIPData):
        """Vessel Movement Connector.

        Args:
            pip_data (PIPData): data from PIP.
        """

        self._iotics_identity: Identity = None
        self._iotics_api: IoticsApi = None
        self._refresh_token_lock: Lock = None
        self._vessel_twin_dict: dict = {}
        self._pip_data: PIPData = pip_data
        # The following will be used to shift a datetime object to a 1 year later
        self._one_year: timedelta = timedelta(days=0)

        self._initialise()

    def _initialise(self):
        """Initialise all the variables of this class. It also starts
        an auto refresh token Thread so the IOTICS token is automatically
        regenerated when it expires.
        """

        log.debug("Initialising Vessel Movement Connector...")
        endpoints = get_host_endpoints(host_url=os.getenv("VESSEL_MOVEMENT_HOST_URL"))
        self._iotics_identity = Identity(
            resolver_url=endpoints.get("resolver"),
            grpc_endpoint=endpoints.get("grpc"),
            user_key_name=os.getenv("USER_KEY_NAME"),
            user_seed=os.getenv("USER_SEED"),
            agent_key_name=os.getenv("VESSEL_MOVEMENT_CONNECTOR_AGENT_KEY_NAME"),
            agent_seed=os.getenv("VESSEL_MOVEMENT_CONNECTOR_AGENT_SEED"),
        )
        log.debug("IOTICS Identity initialised")
        self._iotics_api = IoticsApi(auth=self._iotics_identity)
        log.debug("IOTICS gRPC API initialised")

        self._refresh_token_lock = Lock()

        if self._pip_data.one_year_younger:
            # Adjust for leap years
            self._one_year = timedelta(
                days=365 if datetime.now().year % 4 != 0 else 366
            )

        Thread(
            target=auto_refresh_token,
            args=[self._refresh_token_lock, self._iotics_identity, self._iotics_api],
            name="auto_refresh_token",
            daemon=True,
        ).start()

        self._clear_space()

    def _clear_space(self):
        """Delete all Vessel Twins created by this Connector previously."""

        log.info("Searching for Vessel Twins...")
        search_criteria = self._iotics_api.get_search_payload(
            # The following properties are the ones
            # that are common across all Vessel Twins.
            properties=[
                create_property(
                    key=constant.PROPERTY_KEY_TYPE,
                    value=constant.SHIP_ONTOLOGY,
                    is_uri=True,
                ),
                create_property(
                    constant.PROPERTY_KEY_CREATED_BY,
                    value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
                ),
            ],
        )

        twins_found_list = search_twins(
            search_criteria=search_criteria,
            refresh_token_lock=self._refresh_token_lock,
            iotics_api=self._iotics_api,
            keep_searching=False,
        )

        log.info(
            "Found %d Vessel Twins based on the search criteria", len(twins_found_list)
        )

        log.info("Deleting Vessel Twins...")
        vessel_twin_deleted_count = 0
        for vessel_twin in twins_found_list:
            vessel_twin_id = vessel_twin.twinId.id
            retry_on_exception(
                self._iotics_api.delete_twin,
                "delete_twin",
                self._refresh_token_lock,
                twin_did=vessel_twin_id,
            )

            log.debug("Vessel Twin %s deleted", vessel_twin_id)
            vessel_twin_deleted_count += 1

        log.info("Deleted %s Vessel Twins", vessel_twin_deleted_count)

    def _set_arrival_feed_properties(self, vessel_movement: dict):
        """Get the relevant info from PIP Data to define a
        list of Properties for the Arrival Feed.

        Args:
            vessel_movement (dict): a row in the vessel_movement dataset

        Returns:
            vessel_movement (List[Properties]): list of properties for the Arrival Feed
        """

        eta = self._pip_data.get_eta(vessel_movement)
        eta_datetime = datetime.strptime(eta, constant.DATETIME_FORMAT)
        eta_datetime_plus_one_year = eta_datetime + self._one_year
        berth = self._pip_data.get_berth(vessel_movement)
        port_origin_code = self._pip_data.get_port_of_origin_code(vessel_movement)
        port_origin_name = self._pip_data.get_port_of_origin_name(vessel_movement)
        location_from = self._pip_data.get_pip_area_location_from(vessel_movement)

        arrival_feed_properties = [
            create_property(key=constant.PROPERTY_KEY_LABEL, value="Arrival"),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX + constant.ETA_ONTOLOGY_SUFFIX,
                value=str(eta_datetime_plus_one_year)
                or constant.PROPERTY_DEFAULT_VALUE,
            ),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX + constant.BERTH_ONTOLOGY_SUFFIX,
                value=berth or constant.PROPERTY_DEFAULT_VALUE,
            ),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX
                + constant.PORT_OF_ORIGIN_CODE_ONTOLOGY_SUFFIX,
                value=port_origin_code or constant.PROPERTY_DEFAULT_VALUE,
            ),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX
                + constant.PORT_OF_ORIGIN_NAME_ONTOLOGY_SUFFIX,
                value=port_origin_name or constant.PROPERTY_DEFAULT_VALUE,
            ),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX
                + constant.LOCATION_FROM_ONTOLOGY_SUFFIX,
                value=location_from or constant.PROPERTY_DEFAULT_VALUE,
            ),
        ]

        return arrival_feed_properties

    def _set_departure_feed_properties(self, vessel_movement: dict):
        """Get the relevant info from PIP Data to define a
        list of Properties for the Departure Feed.

        Args:
            vessel_movement (dict): a row in the vessel_movement dataset

        Returns:
            vessel_movement (List[Properties]): list of properties for the Departure Feed
        """

        etd = self._pip_data.get_etd(vessel_movement)
        etd_datetime = datetime.strptime(etd, constant.DATETIME_FORMAT)
        etd_datetime_plus_one_year = etd_datetime + self._one_year
        port_destination_code = self._pip_data.get_port_of_destination_code(
            vessel_movement
        )
        port_destination_name = self._pip_data.get_port_of_destination_name(
            vessel_movement
        )
        location_to = self._pip_data.get_pip_area_location_to(vessel_movement)

        departure_feed_properties = [
            create_property(key=constant.PROPERTY_KEY_LABEL, value="Departure"),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX + constant.ETD_ONTOLOGY_SUFFIX,
                value=str(etd_datetime_plus_one_year)
                or constant.PROPERTY_DEFAULT_VALUE,
            ),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX
                + constant.PORT_OF_DESTINATION_CODE_ONTOLOGY_SUFFIX,
                value=port_destination_code or constant.PROPERTY_DEFAULT_VALUE,
            ),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX
                + constant.PORT_OF_DESTINATION_NAME_ONTOLOGY_SUFFIX,
                value=port_destination_name or constant.PROPERTY_DEFAULT_VALUE,
            ),
            create_property(
                key=constant.PIP_ONTOLOGY_PREFIX + constant.LOCATION_TO_ONTOLOGY_SUFFIX,
                value=location_to or constant.PROPERTY_DEFAULT_VALUE,
            ),
        ]

        return departure_feed_properties

    def _setup_twin_structure(self, vessel_movement: dict) -> TwinStructure:
        """Define the Twin structure in terms of Twin's and Feed's metadata.

        Returns:
            vessel_movement (TwinStructure): an object representing the structure
                of the Vessel Twins.
        """

        twin_structure = None

        ship_name = self._pip_data.get_ship_name(vessel_movement)

        for vessel in self._pip_data.get_vessel_info():
            vessel_name: str = self._pip_data.get_ship_name(vessel)

            if vessel_name.lower() == ship_name.lower():
                abbreviation = self._pip_data.get_abbreviation(vessel)
                vessel_type = self._pip_data.get_vessel_type(vessel)
                co_reference = self._pip_data.get_co_reference(vessel)
                loa = self._pip_data.get_loa(vessel)
                beam = self._pip_data.get_beam(vessel)
                draught = self._pip_data.get_draught(vessel)
                grt = self._pip_data.get_grt(vessel)
                net_tonnage = self._pip_data.get_net_tonnage(vessel)
                port_of_registration = self._pip_data.get_port_of_registration(vessel)
                date_of_registration = self._pip_data.get_date_of_registration(vessel)
                nationality = self._pip_data.get_nationality(vessel)
                dead_weight = self._pip_data.get_dead_weight(vessel)
                lrn = self._pip_data.get_lrn(vessel)

                # Build list of Twin Properties
                twin_properties = [
                    create_property(
                        key=constant.PROPERTY_KEY_TYPE,
                        value=constant.SHIP_ONTOLOGY,
                        is_uri=True,
                    ),
                    create_property(key=constant.PROPERTY_KEY_LABEL, value=ship_name),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.SHIP_NAME_ONTOLOGY_SUFFIX,
                        value=ship_name,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.ABBREVIATION_ONTOLOGY_SUFFIX,
                        value=abbreviation or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.VESSEL_TYPE_ONTOLOGY_SUFFIX,
                        value=vessel_type or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.CO_REFERENCE_ONTOLOGY_SUFFIX,
                        value=co_reference or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX + constant.LOA_ONTOLOGY_SUFFIX,
                        value=loa or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.BEAM_ONTOLOGY_SUFFIX,
                        value=beam or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.DRAUGHT_ONTOLOGY_SUFFIX,
                        value=draught or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX + constant.GRT_ONTOLOGY_SUFFIX,
                        value=grt or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.NET_TONNAGE_ONTOLOGY_SUFFIX,
                        value=net_tonnage or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.PORT_OF_RGISTRATION_ONTOLOGY_SUFFIX,
                        value=port_of_registration or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.DATE_OF_REGISTRATION_ONTOLOGY_SUFFIX,
                        value=date_of_registration or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.NATIONALITY_ONTOLOGY_SUFFIX,
                        value=nationality or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX
                        + constant.DEAD_WEIGHT_ONTOLOGY_SUFFIX,
                        value=dead_weight or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        key=constant.PIP_ONTOLOGY_PREFIX + constant.LRN_ONTOLOGY_SUFFIX,
                        value=lrn or constant.PROPERTY_DEFAULT_VALUE,
                    ),
                    create_property(
                        constant.PROPERTY_KEY_CREATED_BY,
                        value=constant.PROPERTY_VALUE_CREATED_BY_NAME,
                    ),
                    create_property(
                        key=constant.PROPERTY_KEY_HOST_ALLOW_LIST,
                        value=constant.PROPERTY_VALUE_ALLOW_ALL,
                        is_uri=True,
                    ),
                    create_property(
                        key=constant.PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
                        value=constant.PROPERTY_VALUE_ALLOW_ALL,
                        is_uri=True,
                    ),
                ]

                # Set the location of the Vessel Twin.
                # In the future we may think to set the location dynamically.
                twin_location = create_location(
                    lat=constant.PIP_LAT, lon=constant.PIP_LON
                )

                # Set-up Arrival Feed's Metadata
                arrival_feed_properties = self._set_arrival_feed_properties(
                    vessel_movement
                )
                # Set-up Arrival Feed's Value
                arrival_feed_values = [
                    create_value(
                        label=constant.ARRIVAL_FEED_VALUE_LABEL, data_type="boolean"
                    ),
                ]

                # Set-up Departure Feed's Metadata
                departure_feed_properties = self._set_departure_feed_properties(
                    vessel_movement
                )
                # Set-up Departure Feed's Value
                departure_feed_values = [
                    create_value(
                        label=constant.DEPARTURE_FEED_VALUE_LABEL, data_type="boolean"
                    ),
                ]

                # Build final list of Twin's Feeds according to what's defined above
                feeds_list = [
                    create_feed_with_meta(
                        feed_id=constant.ARRIVAL_FEED_ID,
                        properties=arrival_feed_properties,
                        values=arrival_feed_values,
                    ),
                    create_feed_with_meta(
                        feed_id=constant.DEPARTURE_FEED_ID,
                        properties=departure_feed_properties,
                        values=departure_feed_values,
                    ),
                ]

                twin_structure = TwinStructure(
                    properties=twin_properties,
                    location=twin_location,
                    feeds_list=feeds_list,
                )

                break

        return twin_structure

    def _create_twin(self, twin_structure: TwinStructure, ship_name: str) -> str:
        """Create the Vessel Twins given a Twin Structure.

        Args:
            twin_structure (TwinStructure):  Structure of the Vessel Twin to create.
            ship_name (str): name of the Vessel to use as a Twin Key Name.

        Returns:
            str: the Twin DID of the Twin just created.
        """

        ship_twin_key_name = ship_name.lower().replace(" ", "_")
        log.debug("Using Twin Key Name: %s", ship_twin_key_name)

        # Create a new Twin Identity
        twin_registered_identity = (
            self._iotics_identity.create_twin_with_control_delegation(
                twin_key_name=ship_twin_key_name
            )
        )
        twin_did: str = twin_registered_identity.did
        log.debug("Generated new Twin DID: %s", twin_did)

        # Use Upsert Twin operation to create the Twin with Properties
        # and Feeds' objects.
        retry_on_exception(
            self._iotics_api.upsert_twin,
            "upsert_twin",
            self._refresh_token_lock,
            twin_did=twin_did,
            location=twin_structure.location,
            properties=twin_structure.properties,
            feeds=twin_structure.feeds_list,
        )

        log.info("Twin for %s created with DID: %s", ship_name, twin_did)

        self._vessel_twin_dict.update({ship_name: twin_did})
        log.debug("Updated Vessel Twin dictionary")

        return twin_did

    def _share_data(
        self,
        twin_did: str,
        feed_id: str,
        value_to_share: bool = True,
        occurred_at: int = None,
    ):
        """Use Share Feed Data operation.
        What to share is generated dynamically based on the Feed ID passed as input.

        Args:
            twin_did (str): The Twin performing the share.
            feed_id (str): the Feed used to share.
            value_to_share (bool, optional): the actual value shared. Defaults to True.
            occurred_at (int, optional): when the event occurred. If None (default),
                the current datetime will be used.
        """

        data_to_share_value_label = {
            constant.ARRIVAL_FEED_ID: constant.ARRIVAL_FEED_VALUE_LABEL,
            constant.DEPARTURE_FEED_ID: constant.DEPARTURE_FEED_VALUE_LABEL,
        }
        data_to_share = {data_to_share_value_label.get(feed_id): value_to_share}

        # Use the Share Feed Data operation
        retry_on_exception(
            self._iotics_api.share_feed_data,
            "share_feed_data",
            self._refresh_token_lock,
            twin_did=twin_did,
            feed_id=feed_id,
            data=data_to_share,
            occurred_at=occurred_at,
        )

        log.info(
            "Shared %s from Twin DID %s via Feed %s", data_to_share, twin_did, feed_id
        )

        # If a Vessel has arrived to Portsmouth Port (arrived = True),
        # the Departure value needs to be set to 'False'.
        # Be aware this logic is dynamically triggered only if the same Vessel Twin
        # was arrived, then departed on a previous date and now arriving again.
        if feed_id == constant.ARRIVAL_FEED_ID and value_to_share:
            data_to_share = {constant.DEPARTURE_FEED_VALUE_LABEL: False}
            retry_on_exception(
                self._iotics_api.share_feed_data,
                "share_feed_data",
                self._refresh_token_lock,
                twin_did=twin_did,
                feed_id=constant.DEPARTURE_FEED_ID,
                data=data_to_share,
                occurred_at=occurred_at,
            )

            log.info(
                "Shared %s from Twin DID %s via Feed %s",
                data_to_share,
                twin_did,
                feed_id,
            )

    def _schedule_share_data(self, twin_did: str, feed_id: str, vessel_movement: dict):
        """Define when to schedule the Share Feed Data operation.
        If the ATA or ATD are in the future, the Share Feed Data operation is triggered
        at the right time in the future. If the ATA or ATD are in the past,
        the Share Feed Data operation is triggered immediately.

        Args:
            twin_did (str): _description_
            feed_id (str): _description_
            vessel_movement (dict): _description_
        """

        datetime_now = datetime.now()

        # Figure out based on Feed ID which value to get from the vessel movement dataset
        actual_time_to_get = {
            constant.ARRIVAL_FEED_ID: self._pip_data.get_ata(vessel_movement),
            constant.DEPARTURE_FEED_ID: self._pip_data.get_atd(vessel_movement),
        }

        actual_time = actual_time_to_get.get(feed_id)
        actual_time_datetime = datetime.strptime(actual_time, constant.DATETIME_FORMAT)

        # If the actual time vessel data is in the past (+ 1 year), then share it now.
        # Otherwise wait for its actual time before sharing.
        when_to_share = actual_time_datetime + self._one_year
        seconds_before_sharing = max(0, (when_to_share - datetime_now).total_seconds())

        if seconds_before_sharing > 0:
            # Create a Thread object to share vessel data
            # that will start after 'seconds_before_sharing' seconds.
            thread = Timer(
                interval=seconds_before_sharing,
                function=self._share_data,
                args=[twin_did, feed_id],
            )
            thread.name = f"share_{twin_did}_{feed_id}"
            thread.start()

            log.info(
                "Sharing data for Twin DID %s via Feed %s on %s...",
                twin_did,
                feed_id,
                when_to_share,
            )
        else:
            # Convert a datetime into a unix time
            occurred_at_unix_time = int(when_to_share.timestamp())
            self._share_data(twin_did, feed_id, occurred_at=occurred_at_unix_time)

    def _schedule_update_feed(self, twin_did: str, feed_id: str, vessel_movement: dict):
        """Define when to schedule the Update Feed operation (i.e: update Feed's Metadata).
        If the ETA is in the future, the Update Feed operation is triggered
        at the right time in the future. If the ETA is in the past,
        the Update Feed operation is triggered immediately.

        Args:
            twin_did (str): the Twin DID that includes the Feed to be updated.
            feed_id (str): the Feed ID that will be updated.
            vessel_movement (dict): a row in the vessel_movement dataset.
        """

        # Work out based on Feed ID the updated list of Properties
        feed_to_update = {
            constant.ARRIVAL_FEED_ID: self._set_arrival_feed_properties,
            constant.DEPARTURE_FEED_ID: self._set_departure_feed_properties,
        }
        update_feed_property_func = feed_to_update.get(feed_id)
        feed_properties = update_feed_property_func(vessel_movement)

        # Figure out based on Feed ID the list of Properties' Keys that will be updated.
        # In fact, the only way to update Properties is to remove them and add them again.
        properties_keys_updated = {
            constant.ARRIVAL_FEED_ID: [
                constant.PIP_ONTOLOGY_PREFIX + constant.ETA_ONTOLOGY_SUFFIX,
                constant.PIP_ONTOLOGY_PREFIX + constant.BERTH_ONTOLOGY_SUFFIX,
                constant.PIP_ONTOLOGY_PREFIX
                + constant.PORT_OF_ORIGIN_CODE_ONTOLOGY_SUFFIX,
                constant.PIP_ONTOLOGY_PREFIX
                + constant.PORT_OF_ORIGIN_NAME_ONTOLOGY_SUFFIX,
                constant.PIP_ONTOLOGY_PREFIX + constant.LOCATION_FROM_ONTOLOGY_SUFFIX,
            ],
            constant.DEPARTURE_FEED_ID: [
                constant.PIP_ONTOLOGY_PREFIX + constant.ETD_ONTOLOGY_SUFFIX,
                constant.PIP_ONTOLOGY_PREFIX
                + constant.PORT_OF_DESTINATION_CODE_ONTOLOGY_SUFFIX,
                constant.PIP_ONTOLOGY_PREFIX
                + constant.PORT_OF_DESTINATION_NAME_ONTOLOGY_SUFFIX,
                constant.PIP_ONTOLOGY_PREFIX + constant.LOCATION_TO_ONTOLOGY_SUFFIX,
            ],
        }

        eta = self._pip_data.get_eta(vessel_movement)
        eta_datetime = datetime.strptime(eta, constant.DATETIME_FORMAT)
        when_to_update = eta_datetime + self._one_year
        seconds_before_updating = max(
            0, (when_to_update - datetime.now()).total_seconds()
        )

        if seconds_before_updating > 0:
            # Create a Thread object to update vessel feeds' metadata
            # that will start after 'seconds_before_sharing' seconds.
            thread = Timer(
                interval=seconds_before_updating,
                function=self._update_feed,
                args=[twin_did, feed_id, feed_properties, properties_keys_updated],
            )
            thread.name = f"update_{twin_did}_{feed_id}"
            thread.start()

            log.info(
                "Updating Twin DID %s Feed %s on %s...",
                twin_did,
                feed_id,
                when_to_update,
            )
        else:
            self._update_feed(
                twin_did, feed_id, feed_properties, properties_keys_updated
            )

    def _update_feed(
        self, twin_did: str, feed_id: str, feed_properties, properties_keys_updated
    ):
        """Use the Update Feed operation

        Args:
            twin_did (str): the Twin DID that includes the Feed to be updated.
            feed_id (str): the Feed ID that will be updated.
            feed_properties (List[Property]): list of Feed Properties to update.
            properties_keys_updated (List[Property]): list of Feed Properties'Keys
                to replace.
        """

        # Use Update Feed operation
        retry_on_exception(
            self._iotics_api.update_feed,
            "update_feed",
            self._refresh_token_lock,
            twin_did=twin_did,
            feed_id=feed_id,
            props_added=feed_properties,
            props_keys_deleted=properties_keys_updated.get(feed_id),
        )

        log.info("Feed %s of Twin %s updated", feed_id, twin_did)

    def _delete_twin(self, twin_did: str, ship_name: str):
        """Use Delete Twin operation.

        Args:
            twin_did (str): Twin DID to delete.
            ship_name (str): Twin Label of the Twin to delete.
        """

        retry_on_exception(
            self._iotics_api.delete_twin,
            "delete_twin",
            self._refresh_token_lock,
            twin_did=twin_did,
        )

        log.info("Twin DID %s deleted", twin_did)

        # After deleting the Vessel Twin, update its entry
        # in the dictionary with a None value.
        self._vessel_twin_dict.update({ship_name: None})
        log.debug("Updated Vessel Twin dictionary")

    def _schedule_delete_twin(self, twin_did: str, vessel_movement: dict):
        """Define when to schedule the Delete Twin operation.
        If the ATD is in the future, the Delete Twin operation is triggered
        at the right time in the future. If the ATD is in the past,
        the Delete Twin operation is triggered immediately.

        Args:
            twin_did (str): the Twin DID to delete
            vessel_movement (dict): Twin Label of the Twin to delete.
        """

        ship_name = self._pip_data.get_ship_name(vessel_movement)
        atd = self._pip_data.get_atd(vessel_movement)
        atd_datetime = datetime.strptime(atd, constant.DATETIME_FORMAT)

        # Define when to delete the Vessel Twin
        atd_datetime_plus_one_year = atd_datetime + self._one_year
        # The Vessel Twin, to maintain some historical records,
        # can be deleted some days after it is departed from PIP.
        # This is defined by the constant variable 'DELETE_TWIN_AFTER_DAYS'.
        when_to_delete = atd_datetime_plus_one_year + timedelta(
            days=constant.DELETE_TWIN_AFTER_DAYS
        )
        seconds_before_deleting: int = max(
            0, (when_to_delete - datetime.now()).total_seconds()
        )

        if seconds_before_deleting > 0:
            # Create a Thread object to delete the Vessel Twin
            # that will start after 'seconds_before_deleting' seconds.
            delete_twin_thread = Timer(
                interval=seconds_before_deleting,
                function=self._delete_twin,
                args=[twin_did, ship_name],
            )
            delete_twin_thread.name = f"delete_{twin_did}"

            # If a Vessel was scheduled to be deleted in the future,
            # cancel its Delete Twin thread so it can be rescheduled.
            for thread in enumerate_threads():
                if thread.name == delete_twin_thread.name:
                    log.debug("Cancelling deleting Twin thread %s...", thread.name)
                    thread.cancel()

            delete_twin_thread.start()
            log.info("Deleting Vessel Twin DID %s on %s...", twin_did, when_to_delete)
        else:
            self._delete_twin(twin_did, ship_name)

    def start(self, skip_past_vessel_data: bool = False):
        """Scan the vessel movement dataset and process each row individually.
        Check the Estimated Time of Arrival (ETA) to determine
        if it is in the past or the future.
        If the ETA is too far in the past (defined by 'SCHEDULE_PAST_DAYS')
        and 'skip_past_vessel_data' is set to 'True', skip the entry.
        If the ETA is too far in the future (defined by 'SCHEDULE_NEXT_DAYS'),
        pause the iteration until it's time to process the entry.

        Args:
            skip_past_vessel_data (bool, optional): whether or not to skip
                processing past vessel entry. Defaults to False.
        """

        if skip_past_vessel_data:
            log.info("Skipping past Vessel data")

        for vessel_movement in self._pip_data.get_vessel_movement():
            eta = self._pip_data.get_eta(vessel_movement)
            eta_datetime = datetime.strptime(eta, constant.DATETIME_FORMAT)

            log.info("Working on ETA: %s", eta_datetime)
            eta_datetime_plus_one_year = eta_datetime + self._one_year

            # If ETA is too much in the past, skip the entry
            if (
                skip_past_vessel_data
                and eta_datetime_plus_one_year
                < datetime.now() - timedelta(days=constant.SCHEDULE_PAST_DAYS)
            ):
                continue

            # If ETA is too much in the future, wait
            while eta_datetime_plus_one_year > datetime.now() + timedelta(
                days=constant.SCHEDULE_NEXT_DAYS
            ):
                sleep(1)

            ship_name = self._pip_data.get_ship_name(vessel_movement)
            vessel_twin_id = self._vessel_twin_dict.get(ship_name)

            if not vessel_twin_id:
                # A new Vessel Twin needs to be created
                log.info("Creating Vessel Twin for %s...", ship_name)
                vessel_twin_structure = self._setup_twin_structure(vessel_movement)
                vessel_twin_id = self._create_twin(vessel_twin_structure, ship_name)

                # As soon as the Vessel Twin is created,
                # share arrived and departed values to False.

                # Share default value for Arrival Feed
                self._share_data(
                    twin_did=vessel_twin_id,
                    feed_id=constant.ARRIVAL_FEED_ID,
                    value_to_share=False,
                )
                # Share default value for Departure Feed
                self._share_data(
                    twin_did=vessel_twin_id,
                    feed_id=constant.DEPARTURE_FEED_ID,
                    value_to_share=False,
                )
            else:
                # Vessel Twin already existing. Schedule when to update its Feeds' Metadata
                log.info("Vessel Twin for %s already existing", ship_name)
                self._schedule_update_feed(
                    twin_did=vessel_twin_id,
                    feed_id=constant.ARRIVAL_FEED_ID,
                    vessel_movement=vessel_movement,
                )
                self._schedule_update_feed(
                    twin_did=vessel_twin_id,
                    feed_id=constant.DEPARTURE_FEED_ID,
                    vessel_movement=vessel_movement,
                )

            # Schedule share operation for arrival and departure feeds
            self._schedule_share_data(
                twin_did=vessel_twin_id,
                feed_id=constant.ARRIVAL_FEED_ID,
                vessel_movement=vessel_movement,
            )
            self._schedule_share_data(
                twin_did=vessel_twin_id,
                feed_id=constant.DEPARTURE_FEED_ID,
                vessel_movement=vessel_movement,
            )
            # Schedule delete Twin operation
            self._schedule_delete_twin(
                twin_did=vessel_twin_id, vessel_movement=vessel_movement
            )
