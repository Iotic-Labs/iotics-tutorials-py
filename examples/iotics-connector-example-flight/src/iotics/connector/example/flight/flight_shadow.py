import logging
import sys

import constants as constant
from identity import Identity
from iotics.lib.grpc.helpers import create_location, create_property
from iotics.lib.grpc.iotics_api import IoticsApi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


class FlightShadow:
    def __init__(self, iotics_identity: Identity, iotics_api: IoticsApi):
        self._iotics_api: IoticsApi = iotics_identity
        self._iotics_identity: Identity = iotics_api
        self._shadow_twin_did: str = None
        self._country: str = None

    @property
    def country(self) -> str:
        return self._country

    def update_twin(self, new_lat: float, new_lon: float):
        # Update selective sharing permissions
        updated_sharing_permissions = [
            create_property(key=constant.HOST_ALLOW_LIST, value="host_id", is_uri=True),
            create_property(
                key=constant.HOST_METADATA_ALLOW_LIST, value="host_id", is_uri=True
            ),
        ]

        self._iotics_api.update_twin(
            twin_did=self._shadow_twin_did,
            location=create_location(lat=new_lat, lon=new_lon),
            props_added=updated_sharing_permissions,
            props_keys_deleted=[
                twin_prop.key for twin_prop in updated_sharing_permissions
            ],
        )

    def delete_twin(self):
        self._iotics_api.delete_twin(twin_did=self._shadow_twin_did)
