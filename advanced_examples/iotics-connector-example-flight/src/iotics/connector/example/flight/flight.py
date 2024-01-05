from datetime import datetime, timedelta


class Flight:
    def __init__(
        self,
        number: str,
        departure_airport: str,
        departure_time: datetime,
        arrival_airport: str,
        estimated_flight_duration: timedelta,
        meal_service: str,
        airline_identifier: str,
    ):
        self._number: str = number
        self._departure_airport: str = departure_airport
        self._arrival_airport: str = arrival_airport
        self._departure_time: datetime = departure_time
        self._estimated_flight_duration: timedelta = estimated_flight_duration
        self._meal_service: str = meal_service
        self._airline_identifier: str = airline_identifier

    @property
    def number(self) -> str:
        return self._number

    @property
    def departure_airport(self) -> str:
        return self._departure_airport

    @property
    def arrival_airport(self) -> str:
        return self._arrival_airport

    @property
    def departure_time(self) -> datetime:
        return self._departure_time

    @property
    def estimated_flight_duration(self) -> timedelta:
        return self._estimated_flight_duration

    @property
    def airline_identifier(self) -> str:
        return self._airline_identifier
