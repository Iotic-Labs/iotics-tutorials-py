from time import time

from identity import Identity
from iotics.lib.grpc.iotics_api import IoticsApi as IOTICSviagRPC

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

PROPERTY_VALUE_ALLOW_ALL = "http://data.iotics.com/public#all"
PROPERTY_VALUE_ALLOW_NONE = "http://data.iotics.com/public#none"
PROPERTY_VALUE_MODEL = "https://data.iotics.com/app#Model"

UNIT_DEGREE_CELSIUS = "http://qudt.org/vocab/unit/DEG_C"


def auto_refresh_token(identity: Identity, iotics_api: IOTICSviagRPC):
    while True:
        lasted = time() - identity.token_last_updated
        if lasted >= identity.token_duration * 0.75:
            identity.refresh_token()
            iotics_api.update_channel()
