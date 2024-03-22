INDEX_JSON_PATH = "/index.json"
TOKEN_REFRESH_PERIOD_PERCENT = 0.75
RETRYING_ATTEMPTS = 3
RETRY_SLEEP_TIME = 3

# TWIN PROPERTY KEYS
PROPERTY_KEY_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
PROPERTY_KEY_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"
PROPERTY_KEY_CREATED_BY = "https://data.iotics.com/app#createdBy"
PROPERTY_KEY_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PROPERTY_KEY_HOST_ALLOW_LIST = "http://data.iotics.com/public#hostAllowList"
PROPERTY_KEY_HOST_METADATA_ALLOW_LIST = (
    "http://data.iotics.com/public#hostMetadataAllowList"
)

# COMMON CONSTS
PROPERTY_VALUE_CREATED_BY_NAME = "Michael Joseph Jackson"

# GEO COORDINATES
LONDON_LAT = 51.5
LONDON_LON = -0.1

# PUBLISHER CONNECTOR CONSTS
TEMPERATURE_FEED_ID = "temperature"
HUMIDITY_FEED_ID = "humidity"
SENSOR_FEED_VALUE = "reading"
NUMBER_OF_SENSORS = 5
TEMPERATURE_READING_PERIOD = 3
HUMIDITY_READING_PERIOD = 5
MIN_TEMP_VALUE = -10
MAX_TEMP_VALUE = 30
MIN_HUM_VALUE = 0
MAX_HUM_VALUE = 100

# VALUE UNITS
CELSIUS_DEGREES = "http://qudt.org/vocab/unit/DEG_C"
PERCENT = "http://qudt.org/vocab/unit/PERCENT"

# ONTOLOGIES
SENSOR = "https://www.wikidata.org/wiki/Q167676"
