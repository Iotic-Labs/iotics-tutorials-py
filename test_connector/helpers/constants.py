from collections import namedtuple

# UTILITIES CONSTANTS
TOKEN_REFRESH_PERIOD_PERCENT = 0.6
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
PROPERTY_KEY_COLOUR = "https://data.iotics.com/app#color"
PROPERTY_KEY_SPACE_NAME = "https://data.iotics.com/app#spaceName"
PROPERTY_KEY_CREATED_BY = "https://data.iotics.com/app#createdBy"
PROPERTY_KEY_DEFINES = "https://data.iotics.com/app#defines"

# PROPERTY VALUES
PROPERTY_VALUE_ALLOW_ALL = "http://data.iotics.com/public#all"
PROPERTY_VALUE_ALLOW_NONE = "http://data.iotics.com/public#none"
PROPERTY_VALUE_MODEL = "https://data.iotics.com/app#Model"


# REST ENDPOINTS
RestEndpoint = namedtuple("RestEndpoint", ["method", "url"])

GET_HOST_ID = RestEndpoint(method="GET", url="{host}/qapi/host/id")
LIST_TWINS = RestEndpoint(method="GET", url="{host}/qapi/twins")
DELETE_TWIN = RestEndpoint(method="DELETE", url="{host}/qapi/twins/{twin_id}")
UPDATE_TWIN = RestEndpoint(method="PATCH", url="{host}/qapi/twins/{twin_id}")
UPSERT_TWIN = RestEndpoint(method="PUT", url="{host}/qapi/twins")
DESCRIBE_TWIN = RestEndpoint(
    method="GET", url="{host}/qapi/hosts/{host_id}/twins/{twin_id}"
)
DESCRIBE_FEED = RestEndpoint(
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
DESCRIBE_INPUT = RestEndpoint(
    method="GET", url="{host}/qapi/hosts/{host_id}/twins/{twin_id}/inputs/{input_id}"
)
SEND_INPUT_MESSAGE = RestEndpoint(
    method="POST",
    url="{host}/qapi/twins/{twin_sender_id}/interests/hosts/{host_id}/twins/{twin_receiver_id}/inputs/{input_id}/messages",
)
SUBSCRIBE_TO_INPUT = RestEndpoint(
    method=None,
    url="/qapi/twins/{twin_receiver_did}/inputs/{input_id}",
)
SEARCH_TWINS = RestEndpoint(method="POST", url="{host}/qapi/searches")

LAST_SHARED_DATA = RestEndpoint(
    method="GET",
    url="{host}/qapi/twins/{follower_twin_id}/interests/hosts/{publisher_host_id}/twins/{publisher_twin_id}/feeds/{feed_id}/samples/last",
)
