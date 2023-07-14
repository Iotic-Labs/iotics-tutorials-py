"""This script aims to show an example of the creation of a Twin Model.
As you will see throughout this script, the Twin Model is nothing else than 
a normal Twin with a specific Twin Property. It can include Feeds and/or Inputs
but they will only be used by the Twins from Model.
In particular we want to create the Twin Model of a Car Twin with 2 Feeds: Speed and Gas Tank
which will be used by the Twins from Model to share Feed's data.
"""

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
from helpers.identity_interface import IdentityInterface
from helpers.utilities import make_api_call
from iotics.lib.grpc.helpers import create_feed_with_meta, create_property, create_value
from iotics.lib.grpc.iotics_api import IoticsApi
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
    grpc_url: str = iotics_index.get("grpc")

    identity_api: HighLevelIdentityApi = get_rest_high_level_identity_api(
        resolver_url=resolver_url
    )

    identity_interface: IdentityInterface = IdentityInterface(
        grpc_endpoint=grpc_url, identity_api=identity_api
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

    identity_interface.refresh_token(
        user_identity=user_identity, agent_identity=agent_identity, token_duration=60
    )

    iotics_api = IoticsApi(auth=identity_interface)

    twin_car_model_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(
            twin_key_name="TwinCarModel",
            twin_seed=bytes.fromhex(AGENT_SEED),
            agent_registered_identity=agent_identity,
        )
    )

    twin_car_model_did: str = twin_car_model_identity.did

    # Let's define the Twin Properties of the Twin Model
    twin_properties = [
        # The following property is the only one that distinguishes a Twin Model from a different type of Twin.
        # For this reason this should be the first property to add to any Twin Model.
        create_property(key=TYPE, value=TWIN_MODEL, is_uri=True),
        create_property(key=LABEL, value="Car Model", language="en"),
        create_property(key=CREATED_BY, value="Michael Joseph Jackson"),
        # We can define a colour (as hexadecimal value) for the Twin Model
        # so that in the IOTICS UI this Twin and all its Twins from Model
        # will be nicely represented with the same colour.
        create_property(key=COLOUR, value=LIGHT_BLUE),
        # We want to create a Twin Model of a Car, so we can add the 'defines' property
        # with an ontology describing a Car.
        create_property(key=DEFINES, value=CAR, is_uri=True),
        # We also want to define the fuel type of the Car, which for the Twin Model, as a template,
        # we won't set (we will set it for the Twins from Model in exercise #10).
        create_property(key=FUEL_TYPE, value="NOT SET"),
    ]

    # We want to define 2 Feeds for this Twin Model: Speed and Gas Tank
    speed_feed_id: str = "speed"
    value_label: str = "value"
    speed_feed_properties = [create_property(key=LABEL, value="Speed", language="en")]
    speed_feed_values = [
        create_value(
            label=value_label, comment="Speed of the Car", data_type="float", unit=KMH
        )
    ]

    gas_tank_feed_id: str = "gas_tank"
    gas_tank_feed_properties = [
        create_property(key=LABEL, value="Gas Tank", language="en")
    ]
    gas_tank_feed_values = [
        create_value(
            label=value_label,
            comment="Gas left in the tank",
            data_type="float",
            unit=PERCENT,
        )
    ]

    feeds = [
        create_feed_with_meta(
            feed_id=speed_feed_id,
            properties=speed_feed_properties,
            values=speed_feed_values,
        ),
        create_feed_with_meta(
            feed_id=gas_tank_feed_id,
            properties=gas_tank_feed_properties,
            values=gas_tank_feed_values,
        ),
    ]

    # We can now create the Twin Model via the Upsert Twin operation
    iotics_api.upsert_twin(
        twin_did=twin_car_model_did, properties=twin_properties, feeds=feeds
    )

    print(f"Twin Model {twin_car_model_did} created")


if __name__ == "__main__":
    main()
