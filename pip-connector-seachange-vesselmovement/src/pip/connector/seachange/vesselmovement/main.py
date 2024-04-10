from logging import config

from constants import LOGGING_CONFIGURATION
from pip_data import PIPData
from vessel_movement_connector import VesselMovementConnector

config.dictConfig(LOGGING_CONFIGURATION)


def main():
    pip_data: PIPData = PIPData()
    vessel_movement_connector = VesselMovementConnector(pip_data)
    vessel_movement_connector.start(skip_past_vessel_data=True)


if __name__ == "__main__":
    main()
