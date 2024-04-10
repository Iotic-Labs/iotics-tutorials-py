from typing import List

from iotics.api.common_pb2 import GeoLocation, Property
from iotics.api.feed_pb2 import UpsertFeedWithMeta
from iotics.api.input_pb2 import UpsertInputWithMeta


class TwinStructure:
    def __init__(
        self,
        location: GeoLocation = None,
        properties: List[Property] = None,
        feeds_list: List[UpsertFeedWithMeta] = None,
        inputs_list: List[UpsertInputWithMeta] = None,
    ):
        self._location: GeoLocation = location
        self._properties: List[Property] = properties
        self._feeds_list: List[UpsertFeedWithMeta] = feeds_list
        self._inputs_list: List[UpsertInputWithMeta] = inputs_list

    def set_location(self, location: GeoLocation):
        self._location = location

    @property
    def location(self) -> GeoLocation:
        return self._location

    def set_properties(self, properties: List[Property]):
        self._properties = properties

    @property
    def properties(self) -> List[Property]:
        return self._properties

    def set_feeds_list(self, feeds_list: List[UpsertFeedWithMeta]):
        self._feeds_list = feeds_list

    @property
    def feeds_list(self) -> List[UpsertFeedWithMeta]:
        return self._feeds_list

    def set_inputs_list(self, inputs_list: List[UpsertInputWithMeta]):
        self._inputs_list = inputs_list

    @property
    def inputs_list(self) -> List[UpsertInputWithMeta]:
        return self._inputs_list
