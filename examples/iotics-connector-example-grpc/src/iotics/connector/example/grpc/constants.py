from collections import namedtuple

INDEX_JSON_PATH = "/index.json"
TOKEN_REFRESH_PERIOD_PERCENT = 0.75

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

# FLIGHT TWIN
FLIGHT_TWIN_MODEL_LABEL = "Flight Model"
FLIGHT_ONTOLOGY = "https://schema.org/Flight"
FLIGHT_ARRIVAL_AIRPORT = "https://schema.org/arrivalAirport"
FLIGHT_ARRIVAL_TIME = "https://schema.org/arrivalTime"
FLIGHT_DEPARTURE_AIRPORT = "https://schema.org/departureAirport"
FLIGHT_DEPARTURE_TIME = "https://schema.org/departureTime"
FLIGHT_ESTIMATED_FLIGHT_DURATION = "https://schema.org/estimatedFlightDuration"
FLIGHT_NUMBER = "https://schema.org/flightNumber"
FLIGHT_PROVIDER = "https://schema.org/provider"
FLIGHT_FEED_ID = "location"
FLIGHT_FEED_LABEL_LAT = "latitude"
FLIGHT_FEED_LABEL_LON = "longitude"
FLIGHT_COORDINATES = {
    "Location A": {"lat": 12, "lon": 12},
    "Location B": {"lat": 12, "lon": 12},
    "Location C": {"lat": 12, "lon": 12},
    "Location D": {"lat": 12, "lon": 12},
    "Location E": {"lat": 12, "lon": 12},
}
FLIGHT_SHARING_PERIOD_SEC = 5
