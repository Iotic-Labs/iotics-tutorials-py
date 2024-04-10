import csv
import logging
import os
import sys
from typing import List

import constants as constant

log = logging.getLogger(__name__)


class PIPData:
    def __init__(self, one_year_younger: bool = True):
        """PIP Data

        Args:
            one_year_younger (bool, optional): whether or not
                PIP data is 1 year before. Defaults to True.
        """

        self._vessel_movement_list: List[dict] = None
        self._vessel_type_list: List[dict] = None
        self._vessel_movement_filepath: str = None
        self._vessel_info_filepath: str = None
        self._one_year_younger: bool = one_year_younger

        self._initialise()

    @staticmethod
    def _check_global_var(var, var_name: str):
        """Check whether the env var has been set. If not, an error is raised.
        Else its value is returned.

        Args:
            var: the env var to check.
            var_name (str): the name of the env variable.

        Returns:
            The value of the env variable if set.
        """

        if not var:
            logging.error("Parameter %s not set", var_name)
            sys.exit(1)

        return var

    def _initialise(self):
        log.debug("Initialising PIP Data...")

        vessel_movement_file_name_env_var = "VESSEL_MOVEMENT_FILENAME"
        vessel_info_file_name_env_var = "VESSEL_INFO_FILENAME"

        vessel_movement_filename = self._check_global_var(
            var=os.getenv(vessel_movement_file_name_env_var),
            var_name=vessel_movement_file_name_env_var,
        )
        vessel_info_filename = self._check_global_var(
            var=os.getenv(vessel_info_file_name_env_var),
            var_name=vessel_info_file_name_env_var,
        )

        self._vessel_movement_filepath = os.path.join(vessel_movement_filename)
        self._vessel_info_filepath = os.path.join(vessel_info_filename)

        self._vessel_movement_list = []
        self._vessel_type_list = []

        self._load_vessel_movement_data()
        self._load_vessel_info_data()

    @property
    def one_year_younger(self) -> bool:
        return self._one_year_younger

    def get_eta(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_ETA)

    def get_ata(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_ATA)

    def get_etd(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_ETD)

    def get_atd(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_ATD)

    def get_ship_name(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_SHIP_NAME)

    def get_berth(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_BERTH)

    def get_port_of_origin_code(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_PORT_OF_ORIGIN_CODE)

    def get_port_of_origin_name(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_PORT_OF_ORIGIN_NAME)

    def get_pip_area_location_from(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_PIP_AREA_LOCATION_FROM)

    def get_port_of_destination_code(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_PORT_OF_DESTINATION_CODE)

    def get_port_of_destination_name(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_PORT_OF_DESTINATION_NAME)

    def get_pip_area_location_to(self, vessel_movement: dict):
        return vessel_movement.get(constant.FIELD_PIP_AREA_LOCATION_TO)

    def get_abbreviation(self, vessel: dict):
        return vessel.get(constant.FIELD_ABBREVIATION)

    def get_vessel_type(self, vessel: dict):
        return vessel.get(constant.FIELD_TYPE)

    def get_co_reference(self, vessel: dict):
        return vessel.get(constant.FIELD_CO_REFERENCE)

    def get_loa(self, vessel: dict):
        return vessel.get(constant.FIELD_LOA)

    def get_beam(self, vessel: dict):
        return vessel.get(constant.FIELD_BEAM)

    def get_draught(self, vessel: dict):
        return vessel.get(constant.FIELD_DRAUGHT)

    def get_grt(self, vessel: dict):
        return vessel.get(constant.FIELD_GRT)

    def get_net_tonnage(self, vessel: dict):
        return vessel.get(constant.FIELD_NET_TONNAGE)

    def get_port_of_registration(self, vessel: dict):
        return vessel.get(constant.FIELD_PORT_OF_REGISTRATION)

    def get_date_of_registration(self, vessel: dict):
        return vessel.get(constant.FIELD_DATE_OF_REGISTRATION)

    def get_nationality(self, vessel: dict):
        return vessel.get(constant.FIELD_NATIONALITY)

    def get_dead_weight(self, vessel: dict):
        return vessel.get(constant.FIELD_DEAD_WEIGHT)

    def get_lrn(self, vessel: dict):
        return vessel.get(constant.FIELD_LRN)

    def _load_vessel_info_data(self):
        log.info("Processing %s...", self._vessel_info_filepath)

        with open(self._vessel_info_filepath, "r") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                self._vessel_type_list.append(row)

    def _load_vessel_movement_data(self):
        log.info("Processing %s...", self._vessel_movement_filepath)

        with open(self._vessel_movement_filepath, "r") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                self._vessel_movement_list.append(row)

    def get_vessel_movement(self):
        """Return a row from the vessel movement CSV.

        Yields:
            dict: a vessel movement row
        """

        for vessel_movement in self._vessel_movement_list:
            yield vessel_movement

    def get_vessel_info(self):
        """Return a row from the vessel type CSV.

        Yields:
            dict: a vessel info row
        """

        for vessel_type in self._vessel_type_list:
            yield vessel_type
