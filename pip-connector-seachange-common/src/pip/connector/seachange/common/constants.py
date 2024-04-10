# IOTICS consts
INDEX_JSON_PATH = "/index.json"
TOKEN_REFRESH_PERIOD_PERCENT = 0.75
RETRYING_ATTEMPTS = 3
RETRY_SLEEP_TIME = 3

# Twin Property Keys
PROPERTY_KEY_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
PROPERTY_KEY_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"
PROPERTY_KEY_CREATED_BY = "https://data.iotics.com/app#createdBy"
PROPERTY_KEY_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PROPERTY_KEY_HOST_ALLOW_LIST = "http://data.iotics.com/public#hostAllowList"
PROPERTY_KEY_HOST_METADATA_ALLOW_LIST = (
    "http://data.iotics.com/public#hostMetadataAllowList"
)

# Twin Property Values
PROPERTY_VALUE_CREATED_BY_NAME = "Vessel Movement Connector"
PROPERTY_VALUE_ALLOW_ALL = "http://data.iotics.com/public#all"

# Geo Coordinates
PIP_LAT = 50.7951
PIP_LON = -1.1065

# Vessel Movement CSV consts
FIELD_SHIP_NAME = "Ship Name"
FIELD_ETA = "ETA"
FIELD_BERTH = "Berth"
FIELD_PORT_OF_ORIGIN_CODE = "Port Origin Code"
FIELD_PORT_OF_ORIGIN_NAME = "Port Origin Name"
FIELD_PIP_AREA_LOCATION_FROM = "PiP area location from"
FIELD_ETD = "ETD"
FIELD_PORT_OF_DESTINATION_CODE = "Port Destination Code"
FIELD_PORT_OF_DESTINATION_NAME = "Port Destination Name"
FIELD_PIP_AREA_LOCATION_TO = "PiP area location to"
FIELD_ATA = "ATA"
FIELD_ATD = "ATD"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"

# Vessel Type CSV consts
FIELD_ABBREVIATION = "Abbreviation"
FIELD_TYPE = "Type"
FIELD_CO_REFERENCE = "Co. Reference"
FIELD_LOA = "LOA"
FIELD_BEAM = "Beam"
FIELD_DRAUGHT = "Draught"
FIELD_GRT = "Grt"
FIELD_NET_TONNAGE = "Net Tonnag"
FIELD_PORT_OF_REGISTRATION = "Port Of Registration"
FIELD_DATE_OF_REGISTRATION = "Date of Registration"
FIELD_NATIONALITY = "Nationality"
FIELD_DEAD_WEIGHT = "Dead Weight"
FIELD_LRN = "LRN"

# VesselMovementConnector consts
SCHEDULE_NEXT_DAYS = 3
SCHEDULE_PAST_DAYS = 3
DELETE_TWIN_AFTER_DAYS = 3
PROPERTY_DEFAULT_VALUE = "Unknown"
ARRIVAL_FEED_ID = "arrival"
DEPARTURE_FEED_ID = "departure"
ARRIVAL_FEED_VALUE_LABEL = "arrived"
DEPARTURE_FEED_VALUE_LABEL = "departed"

# Ontologies
SHIP_ONTOLOGY = "https://www.wikidata.org/wiki/Q11446"
PIP_ONTOLOGY_PREFIX = "https://w3id.org/SeaChange/PIP#"
SHIP_NAME_ONTOLOGY_SUFFIX = "ShipName"
ABBREVIATION_ONTOLOGY_SUFFIX = "Abbreviation"
VESSEL_TYPE_ONTOLOGY_SUFFIX = "VesselType"
CO_REFERENCE_ONTOLOGY_SUFFIX = "CoReference"
LOA_ONTOLOGY_SUFFIX = "LOA"
BEAM_ONTOLOGY_SUFFIX = "Beam"
DRAUGHT_ONTOLOGY_SUFFIX = "Draught"
GRT_ONTOLOGY_SUFFIX = "GRT"
NET_TONNAGE_ONTOLOGY_SUFFIX = "NetTonnage"
PORT_OF_RGISTRATION_ONTOLOGY_SUFFIX = "PortOfRegistration"
DATE_OF_REGISTRATION_ONTOLOGY_SUFFIX = "DateOfRegistration"
NATIONALITY_ONTOLOGY_SUFFIX = "Nationality"
DEAD_WEIGHT_ONTOLOGY_SUFFIX = "DeadWeight"
LRN_ONTOLOGY_SUFFIX = "LRN"
ETA_ONTOLOGY_SUFFIX = "ETA"
BERTH_ONTOLOGY_SUFFIX = "Berth"
PORT_OF_ORIGIN_CODE_ONTOLOGY_SUFFIX = "PortOfOriginCode"
PORT_OF_ORIGIN_NAME_ONTOLOGY_SUFFIX = "PortOfOriginName"
LOCATION_FROM_ONTOLOGY_SUFFIX = "LocationFrom"
ETD_ONTOLOGY_SUFFIX = "ETD"
PORT_OF_DESTINATION_CODE_ONTOLOGY_SUFFIX = "PortOfDestinationCode"
PORT_OF_DESTINATION_NAME_ONTOLOGY_SUFFIX = "PortOfDestinationName"
LOCATION_TO_ONTOLOGY_SUFFIX = "LocationTo"

# Logging Configurations
LOGGING_LEVEL = "INFO"
LOGGING_CONFIGURATION = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[%(asctime)s] %(levelname)s: %(message)s"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOGGING_LEVEL,
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {"level": LOGGING_LEVEL, "handlers": ["console"]},
}
