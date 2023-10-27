from collections import namedtuple

# UTILITIES CONSTANTS
TOKEN_REFRESH_PERIOD_PERCENT = 0.6
INDEX_JSON_PATH = "/index.json"


# REST ENDPOINTS
RestEndpoint = namedtuple("RestEndpoint", ["method", "url"])

DELETE_TWIN = RestEndpoint(method="DELETE", url="{host}/qapi/twins/{twin_id}")
UPSERT_TWIN = RestEndpoint(method="PUT", url="{host}/qapi/twins")
SHARE_DATA = RestEndpoint(
    method="POST",
    url="{host}/qapi/twins/{twin_id}/feeds/{feed_id}/shares",
)
SEND_INPUT_MESSAGE = RestEndpoint(
    method="POST",
    url="{host}/qapi/twins/{twin_sender_id}/interests/twins/{twin_receiver_id}/inputs/{input_id}/messages",
)
