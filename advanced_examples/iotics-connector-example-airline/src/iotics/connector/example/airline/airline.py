from country import Country


class Airline:
    def __init__(
        self,
        name: str,
        legal_name: str,
        identifier: str,
        hq_country: Country,
        restricted_properties: dict,
        twin_id: str = None,
    ):
        self._name: str = name
        self._legal_name: str = legal_name
        self._identifier: str = identifier
        self._hq_country: Country = hq_country
        self._restricted_properties: dict = restricted_properties
        self._twin_id: str = twin_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def legal_name(self) -> str:
        return self._legal_name

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def hq_country(self) -> Country:
        return self._hq_country

    @property
    def restricted_properties(self) -> dict:
        return self._restricted_properties

    @twin_id.setter
    def twin_id(self, value: str):
        self._twin_id = value

    @property
    def twin_id(self) -> str:
        return self._twin_id
