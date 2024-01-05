class Country:
    def __init__(
        self,
        name: str = "Unknown",
        host_id: str = None,
        lat_min: float = None,
        lat_max: float = None,
        lon_min: float = None,
        lon_max: float = None,
    ):
        self._name: str = name
        self._host_id: str = host_id
        self._lat_min: float = lat_min
        self._lat_max: float = lat_max
        self._lon_min: float = lon_min
        self._lon_max: float = lon_max

    @property
    def name(self) -> str:
        return self._name

    @property
    def host_id(self) -> str:
        return self._host_id

    @property
    def lat_min(self) -> float:
        return self._lat_min

    @property
    def lat_max(self) -> float:
        return self._lat_max

    @property
    def lon_min(self) -> float:
        return self._lon_min

    @property
    def lon_max(self) -> float:
        return self._lon_max
