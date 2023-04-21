from collections import namedtuple

# UTILITIES CONSTANTS
TOKEN_REFRESH_PERIOD_PERCENT = 0.75
INDEX_JSON_PATH = "/index.json"

# PROPERTY KEYS
PROPERTY_KEY_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
PROPERTY_KEY_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"
PROPERTY_KEY_HOST_METADATA_ALLOW_LIST = (
    "http://data.iotics.com/public#hostMetadataAllowList"
)
PROPERTY_KEY_HOST_ALLOW_LIST = "http://data.iotics.com/public#hostAllowList"
PROPERTY_KEY_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PROPERTY_KEY_FROM_MODEL = "https://data.iotics.com/app#model"
PROPERTY_KEY_COLOR = "https://data.iotics.com/app#color"
PROPERTY_KEY_SPACE_NAME = "https://data.iotics.com/app#spaceName"
PROPERTY_KEY_CREATED_BY = "https://data.iotics.com/app#createdBy"

# PROPERTY VALUES
PROPERTY_VALUE_ALLOW_ALL = "http://data.iotics.com/public#all"
PROPERTY_VALUE_ALLOW_NONE = "http://data.iotics.com/public#none"
PROPERTY_VALUE_MODEL = "https://data.iotics.com/app#Model"

# UNIT ONTOLOGIES
UNIT_DEGREE_CELSIUS = "http://qudt.org/vocab/unit/DEG_C"

# REST ENDPOINTS
RestEndpoint = namedtuple("RestEndpoint", ["method", "url"])

GET_HOST_ID = RestEndpoint(method="GET", url="{host}/qapi/host/id")
UPSERT_TWIN = RestEndpoint(method="PUT", url="{host}/qapi/twins")
SHARE_DATA = RestEndpoint(
    method="POST",
    url="{host}/qapi/hosts/{host_id}/twins/{twin_id}/feeds/{feed_id}/shares",
)
SUBSCRIBE_TO_FEED = RestEndpoint(
    method=None,
    url="/qapi/hosts/{twin_follower_host_id}/twins/{twin_follower_did}/interests/hosts/{twin_publisher_host_id}/twins/{twin_publisher_did}/feeds/{feed_id}",
)
SEARCH_TWINS = RestEndpoint(method="POST", url="{host}/qapi/searches")

# LEO DEMO
Location = namedtuple("Location", ["lat", "lon", "host_id", "location_name"])
LOCATION_LIST = [
    Location(
        lat=51.5,
        lon=-0.1,
        host_id="did:iotics:iotQqydwQzMk63eVR1PL8b2NuAUKNCmHDai9",
        location_name="Kansas",
    ),  # demo.dev
    Location(
        lat=48.84,
        lon=2.31,
        host_id="did:iotics:iotAUp5hdAaQrkZEUXMjLud4pJdn6jasuck3",
        location_name="Emerald City",
    ),  # uk-metoffice.dev
    Location(
        lat=52.36,
        lon=4.88,
        host_id="did:iotics:iotPevBWVGxviCez8pFjj5dJrBW1gnWokavs",
        location_name="Gillikin Country",
    ),  # tfl.dev
]

HOST_URL = ""
USER_KEY_NAME = ""
USER_SEED = ""
AGENT_KEY_NAME = ""
AGENT_SEED = ""
