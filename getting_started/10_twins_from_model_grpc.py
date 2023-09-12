"""This script aims to show an example of the creation of 3 Twins from the Model created in exercise #9.
As you will see throughout this script, the Twins from Model are a replication of the components of the
Twin from Model including Twin Properties (with some exceptions), Feeds and/or Inputs. Furtheremore,
Twins from Model should include some logic to handle the sharing of data Feeds and/or receiving Input messages.
"""

from random import randint
from threading import Thread
from time import sleep
from typing import List

from helpers.constants import (
    CAR,
    CREATED_BY,
    DEFINES,
    ELECTRIC_ENGINE,
    FUEL_TYPE,
    INDEX_URL,
    LABEL,
    TWIN_FROM_MODEL,
    TWIN_MODEL,
    TYPE,
    USER_KEY_NAME,
    USER_SEED,
)
from helpers.identity_interface import IdentityInterface
from helpers.utilities import make_api_call
from iotics.lib.grpc.helpers import (
    create_feed_with_meta,
    create_input_with_meta,
    create_property,
)
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

    # First step we want to search for the Twin Model.
    # In order to find the Twin Model we always need at least 1 Twin Property,
    # the one that characterises the Twin Model itself plus an additional search criteria.
    # In this example we will be using as an additional search criteria the Ontology of a Car.
    search_criteria = iotics_api.get_search_payload(
        properties=[
            create_property(key=TYPE, value=TWIN_MODEL, is_uri=True),
            create_property(key=DEFINES, value=CAR, is_uri=True),
            create_property(key=CREATED_BY, value="Michael Joseph Jackson"),
        ],
        response_type="FULL",
    )

    twins_found_list = []
    for response in iotics_api.search_iter(
        client_app_id="search_twins", payload=search_criteria
    ):
        twins = response.payload.twins
        twins_found_list.extend(twins)

    print(f"Found {len(twins_found_list)} Twin(s) based on the search criteria")
    print("---")

    # Hopefully there will be only 1 Twin Model returned by the Search operation
    twin_of_interest = next(iter(twins_found_list))
    # In order to replicate the structure of a Twin Model we need to describe all its components:
    # - Twin Properties (these are returned by the search operation);
    # - Feeds: unfortunately we need to perform a describe Feed operation for each Twin Model's Feed
    # - Inputs: same as above
    twin_model_did: str = twin_of_interest.twinId.id
    twin_model_properties = twin_of_interest.properties
    # Feed and Input IDs are the only info returned by the search operation
    twin_model_feed_ids = twin_of_interest.feeds
    twin_model_input_ids = twin_of_interest.inputs

    # We want to perform a Describe Feed operation for each Feed so we can eventually
    # store these info to create Twins from Model
    twin_model_feeds: List[dict] = []
    for twin_model_feed in twin_model_feed_ids:
        feed_id: str = twin_model_feed.feedId.id
        feed_description = iotics_api.describe_feed(
            twin_did=twin_model_did, feed_id=feed_id
        )
        twin_model_feeds.append(feed_description)

    # Although our Twin Model doesn't include any Inputs, just for completeness
    # the following is the code to retrieve the Input description
    twin_model_inputs: List[dict] = []
    for twin_model_input in twin_model_input_ids:
        input_id: str = twin_model_input.inputId.id
        input_description = iotics_api.describe_input(
            twin_did=twin_model_did, input_id=input_id
        )
        twin_model_inputs.append(input_description)

    # We can define a function that will be used to share Feed data by the Twins from Model
    def share_data(twin_id: str, feed_id: str):
        while True:
            try:
                # We can generate a random integer between 0 and 100 to be shared via the Twin from Model's feed
                data_to_share: dict = {"value": randint(0, 100)}
                # Use the Share Feed data operation
                iotics_api.share_feed_data(
                    twin_did=twin_id, feed_id=feed_id, data=data_to_share
                )
                print(f"Shared {data_to_share} from Twin {twin_id} via Feed {feed_id}")
                sleep(5)
            except KeyboardInterrupt:
                break

    share_data_thread_list: List[Thread] = []

    # We are now ready to create our 3 Twins from Model
    for car_n in range(3):
        # Let's start by creating a Twin Identity for each Twin
        twin_car_identity: RegisteredIdentity = (
            identity_api.create_twin_with_control_delegation(
                twin_key_name=f"TwinCar{car_n}",
                twin_seed=bytes.fromhex(AGENT_SEED),
                agent_registered_identity=agent_identity,
            )
        )

        # Next step is to start defining the Twin Properties of each Twin from Model.
        # Not all the Twin Model's properties should be replicated to its children.
        # In particular, the Label, Comment and other Twin's specific properties can change,
        # so let's start creating a list of Properties specific for this Twin.
        twin_car_properties = [
            # Similar to the property that characterises a Twin Model, each Twin from Model
            # must contain the following property that specifies that this Twin is a child of
            # a specific Twin Model DID.
            create_property(key=TWIN_FROM_MODEL, value=twin_model_did, is_uri=True),
            create_property(key=LABEL, value=f"Twin Car {car_n+1}", language="en"),
            create_property(key=TYPE, value=CAR, is_uri=True),
        ]

        # Now we can scan the Twin Model's property list so we can use them to build
        # our Twin from Model.
        for twin_model_property in twin_model_properties:
            # Among all the Twin Model's properties we want to skip:
            # - the specific property of a Twin Model (type = Model)
            # - Label since we defined it above
            # - Defines, since it refers to the Ontology definition
            # in the Twin Model only
            if twin_model_property.key in [TYPE, LABEL, DEFINES]:
                continue

            # We can now define the fuel type property that we didn't set for the Twin Model.
            # In particular we can use the semantic description of an 'electric engine'.
            if twin_model_property.key == FUEL_TYPE:
                new_property = create_property(
                    key=FUEL_TYPE, value=ELECTRIC_ENGINE, is_uri=True
                )
                twin_car_properties.append(new_property)
                continue

            # Add to the list all the other Twin Model's property
            twin_car_properties.append(twin_model_property)

        # After defining the Twin Properties we can now work on the Feeds.
        # Fortunately Feeds (and Inputs) must be replicated without any exception on Properties and Values,
        # so the process is a little easier.
        twin_car_feeds = []
        for twin_model_feed in twin_model_feeds:
            feed_id: str = twin_model_feed.payload.feedId.id
            store_last: bool = twin_model_feed.payload.result.storeLast
            feed_properties = twin_model_feed.payload.result.properties
            feed_values = twin_model_feed.payload.result.values
            twin_car_feeds.append(
                create_feed_with_meta(
                    feed_id=feed_id,
                    store_last=store_last,
                    properties=feed_properties,
                    values=feed_values,
                )
            )

            # For each Feed we want to create a Thread that handles the logic of sharing data
            th = Thread(
                target=share_data, args=[twin_car_identity.did, feed_id], daemon=True
            )

            # We havent created the Twin from Model yet, so we can't start the thread !!
            # However we can collect all the threads into a list so we can start them after the Twin is created.
            share_data_thread_list.append(th)

        # Our Twin Model doesn't include any Inputs. Look at the following section only for completeness
        twin_car_inputs = []
        for twin_model_input in twin_model_inputs:
            input_id: str = twin_model_input.payload.inputId.id
            input_properties = twin_model_input.payload.result.properties
            input_values = twin_model_input.payload.result.values
            twin_car_inputs.append(
                create_input_with_meta(
                    input_id=input_id, properties=input_properties, values=input_values
                )
            )

        # We can now use the Upsert Twin operation to create the Twin from Model
        iotics_api.upsert_twin(
            twin_did=twin_car_identity.did,
            properties=twin_car_properties,
            feeds=twin_car_feeds,
            inputs=twin_car_inputs,
        )

        print(f"Twin Car {twin_car_identity.did} created")

    # All the Twins are now created so we can start the threads that will allow them to share data
    for share_data_thread in share_data_thread_list:
        share_data_thread.start()

    while True:
        try:
            sleep(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
