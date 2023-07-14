"""This script aims to show an example of the creation of a Twin Model.
As you will see throughout this script, the Twin Model is nothing else than 
a normal Twin with a specific Twin Property. It can include Feeds and/or Inputs
but they will only be used by the Twins from Model.
In particular we want to create the Twin Model of a Car Twin with 2 Feeds: Speed and Gas Tank
which will be used by the Twins from Model to share Feed's data.
"""

from typing import List

from helpers.constants import (
    CAR,
    COLOUR,
    CREATED_BY,
    DEFINES,
    FUEL_TYPE,
    INDEX_URL,
    KMH,
    LABEL,
    LIGHT_BLUE,
    PERCENT,
    TWIN_MODEL,
    TYPE,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.utilities import make_api_call
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)

HOST_URL: str = ""

AGENT_KEY_NAME: str = ""
AGENT_SEED: str = ""


def main():
    iotics_index: dict = make_api_call(
        method="GET", endpoint=INDEX_URL.format(host_url=HOST_URL)
    )
    resolver_url: str = iotics_index.get("resolver")
    identity_api: HighLevelIdentityApi = get_rest_high_level_identity_api(
        resolver_url=resolver_url
    )

    (
        user_identity,
        agent_identity,
    ) = identity_api.create_user_and_agent_with_auth_delegation(
        user_seed=bytes.fromhex(USER_SEED),
        user_key_name=USER_KEY_NAME,
        agent_seed=bytes.fromhex(AGENT_SEED),
        agent_key_name=AGENT_KEY_NAME,
    )

    token: str = identity_api.create_agent_auth_token(
        user_did=user_identity.did,
        agent_registered_identity=agent_identity,
        duration=60,
    )

    headers: dict = {
        "accept": "application/json",
        "Iotics-ClientAppId": "twin_model",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    twin_car_model_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(
            twin_key_name="TwinCarModel",
            twin_seed=bytes.fromhex(AGENT_SEED),
            agent_registered_identity=agent_identity,
        )
    )

    twin_car_model_did: str = twin_car_model_identity.did

    # Let's define the Twin Properties of the Twin Model
    twin_properties: List[dict] = [
        # The following property is the only one that distinguishes a Twin Model from a different type of Twin.
        # For this reason this should be the first property to add to any Twin Model.
        {"key": TYPE, "uriValue": {"value": TWIN_MODEL}},
        {"key": LABEL, "langLiteralValue": {"value": "Car Model", "lang": "en"}},
        {"key": CREATED_BY, "stringLiteralValue": {"value": "Michael Joseph Jackson"}},
        # We can define a colour (as hexadecimal value) for the Twin Model
        # so that in the IOTICS UI this Twin and all its Twins from Model
        # will be nicely represented with the same colour.
        {"key": COLOUR, "stringLiteralValue": {"value": LIGHT_BLUE}},
        # We want to create a Twin Model of a Car, so we can add the 'defines' property
        # with an ontology describing a Car.
        {"key": DEFINES, "uriValue": {"value": CAR}},
        # We also want to define the fuel type of the Car, which for the Twin Model, as a template,
        # we won't set (we will set it for the Twins from Model in exercise #10).
        {"key": FUEL_TYPE, "stringLiteralValue": {"value": "NOT SET"}},
    ]

    # We want to define 2 Feeds for this Twin Model: Speed and Gas Tank
    speed_feed_id: str = "speed"
    value_label: str = "value"
    speed_feed_properties: List[dict] = [
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Speed", "lang": "en"},
        },
    ]
    speed_feed_values: List[dict] = [
        {
            "comment": "Speed of the car",
            "dataType": "float",
            "label": value_label,
            "unit": KMH,
        }
    ]

    gas_tank_feed_id: str = "gas_tank"
    gas_tank_feed_properties: List[dict] = [
        {
            "key": LABEL,
            "langLiteralValue": {"value": "Gas Tank", "lang": "en"},
        },
    ]
    gas_tank_feed_values: List[dict] = [
        {
            "comment": "Gas left in the tank",
            "dataType": "float",
            "label": value_label,
            "unit": PERCENT,
        }
    ]

    feeds: List[dict] = [
        {
            "id": speed_feed_id,
            "storeLast": True,
            "properties": speed_feed_properties,
            "values": speed_feed_values,
        },
        {
            "id": gas_tank_feed_id,
            "storeLast": True,
            "properties": gas_tank_feed_properties,
            "values": gas_tank_feed_values,
        },
    ]

    # We can now create the Twin Model via the Upsert Twin operation
    upsert_twin_payload: dict = {
        "twinId": {"id": twin_car_model_did},
        "properties": twin_properties,
        "feeds": feeds,
    }

    make_api_call(
        method="PUT",
        endpoint=f"{HOST_URL}/qapi/twins",
        headers=headers,
        payload=upsert_twin_payload,
    )

    print(f"Twin Model {twin_car_model_did} created")


if __name__ == "__main__":
    main()
