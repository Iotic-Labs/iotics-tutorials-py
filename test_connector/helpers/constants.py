from collections import namedtuple
import os

# UTILITIES CONSTANTS
TOKEN_REFRESH_PERIOD_PERCENT = 0.75


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

# TEST CONNECTOR
FEED_ID = "feed_id"
FEED_LABEL = "feed_label"
INPUT_ID = "input_id"
INPUT_LABEL = "input_label"

# ENV VARS
USER_NAME_ACCESS = ""
USER_PASS_ACCESS = ""
HTTP_PROXY = ""
HTTPS_PROXY = ""

# USER_NAME_ACCESS = os.environ["USER_NAME_ACCESS"]
# USER_PASS_ACCESS = os.environ["USER_PASS_ACCESS"]
# HTTP_PROXY = os.environ["HTTP_PROXY"]
# HTTPS_PROXY = os.environ["HTTPS_PROXY"]

# HOST
HOST_URL = "https://demo.dev.iotics.space"
RESOLVER_URL = "https://did.stg.iotics.com"
STOMP_URL = "wss://demo.dev.iotics.space/ws"

USER_KEY_NAME = "00"
USER_SEED = "a7631ed56882044021224d06c8deb966afb6a5db2115c805900b02c35b8188ce"
AGENT_KEY_NAME = "00"
AGENT_SEED = "e8da559d6197e3160d48c901db985e1b32984c7c72c2613a5e1cf7692e6e6e48"
