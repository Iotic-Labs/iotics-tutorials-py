INDEX_JSON_PATH = "/index.json"
TOKEN_REFRESH_PERIOD_PERCENT = 0.75
RETRY_SLEEP_TIME = 3
SEARCH_NEW_FLIGHTS_SLEEP_TIME = 600
RETRYING_ATTEMPTS = 3

# TWIN PROPERTY KEYS
LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"
CREATED_BY = "https://data.iotics.com/app#createdBy"
UPDATED_BY = "https://data.iotics.com/app#updatedBy"
DEFINES = "https://data.iotics.com/app#defines"
TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
TWIN_FROM_MODEL = "https://data.iotics.com/app#model"
COLOUR = "https://data.iotics.com/app#color"
HOST_ALLOW_LIST = "http://data.iotics.com/public#hostAllowList"
HOST_METADATA_ALLOW_LIST = "http://data.iotics.com/public#hostMetadataAllowList"
SPACE_NAME = "https://data.iotics.com/app#spaceName"
HAS_PROJECT_NAME = "http://data.iotics.com/pip_demo#hasProjectName"

# TWIN PROPERTY VALUES
TWIN_MODEL = "https://data.iotics.com/app#Model"
ALLOW_ALL = "http://data.iotics.com/public#all"
ALLOW_NONE = "http://data.iotics.com/public#none"
PROJECT_NAME = "IOTICS Connector Example"

# AIRLINE TWIN
AIRLINE_INPUT_ID = "new_location"
AIRLINE_TWIN_MODEL_LABEL = "Airline Model"
AIRLINE_ONTOLOGY = "https://schema.org/Airline"
AIRLINE_LEGAL_NAME = "https://schema.org/legalName"
AIRLINE_IDENTIFIER = "https://schema.org/identifier"
AIRLINE_LOCATION = "https://schema.org/location"
AIRLINE_INPUT_LABEL = "flight_twin_did"
AIRLINE_IDENTIFIERS = ["Airline ABC", "Airline DEF"]

# FLIGHT TWIN
FLIGHT_TWIN_MODEL_LABEL = "Flight Model"
FLIGHT_ONTOLOGY = "https://schema.org/Flight"
FLIGHT_ARRIVAL_AIRPORT = "https://schema.org/arrivalAirport"
FLIGHT_ARRIVAL_TIME = "https://schema.org/arrivalTime"
FLIGHT_DEPARTURE_AIRPORT = "https://schema.org/departureAirport"
FLIGHT_DEPARTURE_TIME = "https://schema.org/departureTime"
ESTIMATED_FLIGHT_DURATION = "https://schema.org/estimatedFlightDuration"
FLIGHT_NUMBER = "https://schema.org/flightNumber"
FLIGHT_PROVIDER = "https://schema.org/provider"
FLIGHT_AIRCRAFT = "https://schema.org/aircraft"
FLIGHT_MEAL_SERVICE = "https://schema.org/mealService"
FLIGHT_FEED_ID = "location"
FLIGHT_FEED_LABEL_LAT = "latitude"
FLIGHT_FEED_LABEL_LON = "longitude"
AIRPORT_COORDINATES = [
    {"name": "London Heathrow Airport", "coords": {"lat": 51.4694, "lon": -0.4503}},
    {"name": "Manchester Airport", "coords": {"lat": 53.3651, "lon": -2.2722}},
    {"name": "Charles de Gaulle Airport", "coords": {"lat": 49.0097, "lon": 2.5479}},
    {
        "name": "Vienna International Airport",
        "coords": {"lat": 48.1176, "lon": 16.5668},
    },
    {"name": "Barcelona-El Prat Airport", "coords": {"lat": 41.2974, "lon": 2.0833}},
]
FLIGHT_SHARING_PERIOD_SEC = 5

# COUNTRIES
UK_LAT_MIN = 49.8625
UK_LAT_MAX = 61.0146
UK_LON_MIN = -9.2263
UK_LON_MAX = 2.2241
UK_HOST_ID = ""

FRANCE_LAT_MIN = 41.303
FRANCE_LAT_MAX = 51.124
FRANCE_LON_MIN = -5.725
FRANCE_LON_MAX = 9.561
FRANCE_HOST_ID = ""

SPAIN_LAT_MIN = 35.9515
SPAIN_LAT_MAX = 43.7649
SPAIN_LON_MIN = -9.3921
SPAIN_LON_MAX = 3.0395
SPAIN_HOST_ID = ""

GERMANY_LAT_MIN = 47.2701
GERMANY_LAT_MAX = 55.0582
GERMANY_LON_MIN = 5.8663
GERMANY_LON_MAX = 15.0419
GERMANY_HOST_ID = ""

AUSTRIA_LAT_MIN = 46.3727
AUSTRIA_LAT_MAX = 49.0205
AUSTRIA_LON_MIN = 9.5401
AUSTRIA_LON_MAX = 17.1601
AUSTRIA_HOST_ID = ""
