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

# Common Consts
PROPERTY_VALUE_CREATED_BY_NAME = "Michael Joseph Jackson"

# Geo Coordinates
LONDON_LAT = 51.5
LONDON_LON = -0.1

# Publisher Connector Consts
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

# Synthesiser Connector Consts
CALCULATION_PERIOD_SEC = 10
AVERAGE_FEED_ID = "average"
AVERAGE_TEMPERATURE_FEED_VALUE = "avg_temperature"
AVERAGE_HUMIDITY_FEED_VALUE = "avg_humidity"
MIN_MAX_FEED_ID = "min_max"
MIN_TEMPERATURE_FEED_VALUE = "min_temperature"
MAX_TEMPERATURE_FEED_VALUE = "max_temperature"
MIN_HUMIDITY_FEED_VALUE = "min_humidity"
MAX_HUMIDITY_FEED_VALUE = "max_humidity"

# Databypass Connector Consts
SENDER_TWIN_ID_VALUE = "sender_twin_id"
VERIFICATION_INFO_INPUT_ID = "VerificationInput"
ORGANISATION_VALUE = "IOTICS"
EMAIL_ADDRESS_VALUE = "abc@iotics.com"
ORGANISATIONS_ALLOWED_LIST = ["IOTICS"]
DB_ACCESS_INFO_INPUT_ID = "DBAccessInfo"
DB_NAME_INPUT_VALUE = "db_name"
DB_USERNAME_INPUT_VALUE = "db_username"
DB_PASSWORD_INPUT_VALUE = "db_password"
ACCESS_DB_PERIOD = 10

# Value Units
CELSIUS_DEGREES = "http://qudt.org/vocab/unit/DEG_C"
PERCENT = "http://qudt.org/vocab/unit/PERCENT"

# Ontologies
SENSOR = "https://www.wikidata.org/wiki/Q167676"
TEMPERATURE = "https://www.wikidata.org/wiki/Q11466"
HUMIDITY = "https://www.wikidata.org/wiki/Q180600"
DATA_STORE = "https://www.wikidata.org/wiki/Q80428"
MEAN_VALUE = "https://www.wikidata.org/wiki/Q2796622"
MAX_VALUE = "https://schema.org/maxValue"
MIN_VALUE = "https://schema.org/minValue"
DATA_ACCESS = "https://www.wikidata.org/wiki/Q5227230"
VERIFICATION = "https://www.wikidata.org/wiki/Q953429"
REQUEST = "https://www.wikidata.org/wiki/Q22445448"
FULL_NAME = "https://www.wikidata.org/wiki/Q1071027"
ORGANISATION = "https://www.wikidata.org/wiki/Q43229"
EMAIL_ADDRESS = "https://www.wikidata.org/wiki/Q1273217"

# Datetime formats
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# DB settings
DB_URL = "postgresql://{username}:{password}@postgres:5432/{db_name}"

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
