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

# TWIN PROPERTY VALUES
TWIN_MODEL = "https://data.iotics.com/app#Model"
ALLOW_ALL = "http://data.iotics.com/public#all"
ALLOW_NONE = "http://data.iotics.com/public#none"
PROJECT_NAME = "IOTICS Connector Example"

# HQ TWIN
HQ_INPUT_ID = "new_location"
HQ_NEW_LAT_INPUT_LABEL = "new_lat"
HQ_NEW_LON_INPUT_LABEL = "new_lon"
HQ_DRONE_DID_INPUT_LABEL = "twin_did"

# UK HQ TWIN
Location = namedtuple(
    "Location", ["lat_min", "lat_max", "lon_min", "lon_max", "host_id"]
)
LOCATION_LIST = {
    "local": Location(
        lat_min=51.5,
        lat_max=51.5,
        lon_min=-0.1,
        lon_max=-0.1,
        host_id="",
    ),  # demo.dev
    "Kansas": Location(
        lat_min=48.84,
        lat_max=48.84,
        lon_min=2.31,
        lon_max=2.31,
        host_id="",
    ),  # uk-metoffice.dev
    "Emerald City": Location(
        lat_min=52.36,
        lat_max=52.36,
        lon_min=4.88,
        lon_max=4.88,
        host_id="",
    ),  # tfl.dev
}


# IOTICSPACE INFO
INDEX_URL = "/index.json"

# REST ENDPOINTS
RestEndpoint = namedtuple("RestEndpoint", ["method", "url"])

DELETE_TWIN = RestEndpoint(method="DELETE", url="{host}/qapi/twins/{twin_id}")
UPDATE_TWIN = RestEndpoint(method="PATCH", url="{host}/qapi/twins/{twin_id}")
UPSERT_TWIN = RestEndpoint(method="PUT", url="{host}/qapi/twins")
DESCRIBE_TWIN_LOCAL = RestEndpoint(method="GET", url="{host}/qapi/twins/{twin_id}")
DESCRIBE_TWIN_REMOTE = RestEndpoint(
    method="GET", url="{host}/qapi/hosts/{host_id}/twins/{twin_id}"
)
DESCRIBE_FEED_LOCAL = RestEndpoint(
    method="GET", url="{host}/qapi/twins/{twin_id}/feeds/{feed_id}"
)
DESCRIBE_FEED_REMOTE = RestEndpoint(
    method="GET", url="{host}/qapi/hosts/{host_id}/twins/{twin_id}/feeds/{feed_id}"
)
SHARE_DATA = RestEndpoint(
    method="POST",
    url="{host}/qapi/twins/{twin_id}/feeds/{feed_id}/shares",
)
SUBSCRIBE_TO_FEED = RestEndpoint(
    method=None,
    url="/qapi/twins/{twin_follower_did}/interests/hosts/{twin_publisher_host_id}/twins/{twin_publisher_did}/feeds/{feed_id}",
)
DESCRIBE_INPUT_LOCAL = RestEndpoint(
    method="GET", url="{host}/qapi/twins/{twin_id}/inputs/{input_id}"
)
DESCRIBE_INPUT_REMOTE = RestEndpoint(
    method="GET", url="{host}/qapi/hosts/{host_id}/twins/{twin_id}/inputs/{input_id}"
)
SEND_INPUT_MESSAGE_LOCAL = RestEndpoint(
    method="POST",
    url="{host}/qapi/twins/{twin_sender_id}/interests/twins/{twin_receiver_id}/inputs/{input_id}/messages",
)
SEND_INPUT_MESSAGE_REMOTE = RestEndpoint(
    method="POST",
    url="{host}/qapi/twins/{twin_sender_id}/interests/hosts/{host_id}/twins/{twin_receiver_id}/inputs/{input_id}/messages",
)
SUBSCRIBE_TO_INPUT = RestEndpoint(
    method=None,
    url="/qapi/twins/{twin_receiver_did}/inputs/{input_id}",
)
SEARCH_TWINS = RestEndpoint(method="POST", url="{host}/qapi/searches")
