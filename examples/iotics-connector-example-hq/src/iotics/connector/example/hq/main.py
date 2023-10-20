import logging
import os
import sys

import constants as constant
from identity import Identity
from iotics.lib.grpc.helpers import (
    create_input_with_meta,
    create_property,
    create_value,
)
from iotics.lib.grpc.iotics_api import IoticsApi
from utilities import get_host_endpoints

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


def main():
    endpoints = get_host_endpoints(host_url=os.getenv("HQ_HOST_URL"))
    identity = Identity(
        resolver_url=endpoints.get("resolver"),
        grpc_endpoint=endpoints.get("grpc"),
        user_key_name=os.getenv("USER_KEY_NAME"),
        user_seed=os.getenv("USER_SEED"),
        agent_key_name=os.getenv("HQ_AGENT_KEY_NAME"),
        agent_seed=os.getenv("HQ_AGENT_SEED"),
    )
    iotics_api = IoticsApi(auth=identity)
    identity.set_grpc_api(grpc_api=iotics_api)

    # Generate a new Twin Registered Identity for the HQ Twin Model
    hq_twin_model_identity = identity.create_twin_with_control_delegation(
        twin_key_name="HQTwinModel"
    )

    # Define Twin Model's Metadata
    twin_model_label = "HQ Model"
    twin_model_properties = [
        create_property(key=constant.TYPE, value=constant.TWIN_MODEL, is_uri=True),
        create_property(key=constant.CREATED_BY, value="HQ Connector Example"),
        create_property(key=constant.UPDATED_BY, value="HQ Connector Example"),
        create_property(key=constant.LABEL, value=twin_model_label, language="en"),
    ]

    # Define Twin Model's Input
    inputs = [
        create_input_with_meta(
            input_id=constant.HQ_INPUT_ID,
            properties=[
                create_property(key=constant.LABEL, value="New Location", language="en")
            ],
            values=[
                create_value(
                    label=constant.HQ_NEW_LAT_INPUT_LABEL,
                    comment="New Latitude",
                    data_type="float",
                ),
                create_value(
                    label=constant.HQ_NEW_LON_INPUT_LABEL,
                    comment="New Longitude",
                    data_type="float",
                ),
                create_value(
                    label=constant.HQ_DRONE_DID_INPUT_LABEL,
                    comment="Drone's Twin DID",
                    data_type="string",
                ),
            ],
        ),
    ]

    # Upsert Twin
    iotics_api.upsert_twin(
        twin_did=hq_twin_model_identity.did,
        properties=twin_model_properties,
        inputs=inputs,
    )

    logging.info("%s Twin created: %s", twin_model_label, hq_twin_model_identity.did)

    # # Generate a new Twin Registered Identity for the HQ Twin UK
    # hq_twin_uk_identity = identity.create_twin_with_control_delegation(
    #     twin_key_name="HQTwinUK"
    # )

    # # Define the Twin Properties that will be different from the Twin Model's
    # twin_label = "HQ UK"
    # twin_properties = [
    #     create_property(
    #         key=constant.TWIN_FROM_MODEL,
    #         value=hq_twin_model_identity.did,
    #         is_uri=True,
    #     ),
    #     create_property(key=constant.LABEL, value=twin_label, language="en"),
    # ]

    # # The HQ Twin's Properties will be the same as the Twin Models',
    # # except the ones we defined above and some other exceptions.
    # for twin_model_property in twin_model_properties:
    #     if twin_model_property.key in [
    #         constant.TYPE,
    #         constant.LABEL,
    #         constant.DEFINES,
    #         constant.HOST_ALLOW_LIST,
    #         constant.HOST_METADATA_ALLOW_LIST,
    #     ]:
    #         continue

    #     twin_properties.append(twin_model_property)

    # # Upsert Twin
    # iotics_api.upsert_twin(
    #     twin_did=hq_twin_uk_identity.did, properties=twin_properties, inputs=inputs
    # )

    # logging.info("%s Twin created: %s", twin_label, hq_twin_uk_identity.did)

    # shadow_twins: dict = {}

    # def create_shadow(drone_twin_did: str, twin_description):
    #     # TODO
    #     print()

    # def take_action(iotics_api: IoticsApi, drone_twin_did: str):
    #     twin_description = iotics_api.describe_twin(twin_did=drone_twin_did)

    #     twin_location = twin_description.payload.result.location
    #     local_borders = constant.LOCATION_LIST.get("local")

    #     # Create/Update Shadow if the drone's location is outside
    #     # the related country's border
    #     if not (
    #         local_borders.lat_min < float(twin_location.lat) < local_borders.lat_max
    #         or local_borders.lon_min < float(twin_location.lon) < local_borders.lon_max
    #     ):
    #         shadow_twin = shadow_twins.get(drone_twin_did)

    #         if not shadow_twin:
    #             # Create new Shadow
    #             create_shadow(
    #                 twin_description=twin_description,
    #                 original_twin_did=drone_twin_did,
    #                 twin_location=twin_location,
    #             )

    #         # Update existing Shadow
    #         elif shadow_twin.get("lat") != float(twin_location.lat):
    #             update_shadow(
    #                 original_twin_did=original_twin_did, twin_location=twin_location
    #             )
    #     # Twin back to Base
    #     else:
    #         delete_shadow(original_twin_did=original_twin_did)

    # def wait_for_new_locations(iotics_api: IoticsApi, input_listener):
    #     """Receive Input data and take action

    #     Args:
    #         iotics_api (IoticsApi): an instance of IoticsApi used to perform the 'share_feed_data' operation
    #         input_listener (Iterator): used to get new data samples sent by the App UI Twin.
    #     """

    #     for latest_input_data in input_listener:
    #         data_received = json.loads(latest_input_data.payload.message.data)
    #         new_latitude = data_received.get(constant.HQ_NEW_LAT_INPUT_LABEL)
    #         new_longitude = data_received.get(constant.HQ_NEW_LON_INPUT_LABEL)
    #         drone_twin_did = data_received.get(constant.HQ_DRONE_DID_INPUT_LABEL)

    #         logging.info(
    #             "Received new location from Drone Twin %s: (%f, %f)",
    #             drone_twin_did,
    #             new_latitude,
    #             new_longitude,
    #         )

    # def get_input_listener(iotics_api: IoticsApi, hq_twin_did: str):
    #     """Get a new Feed input_listener anytime the IOTICS token expires. When that happens,
    #     generate a new input_listener.

    #     Args:
    #         iotics_api (IoticsApi): an instance of IoticsApi used to perform IOTICS operations.
    #     """

    #     while True:
    #         input_listener = iotics_api.receive_input_messages(
    #             twin_did=hq_twin_did, input_id=constant.HQ_INPUT_ID
    #         )

    #         try:
    #             wait_for_new_locations(
    #                 iotics_api=iotics_api, input_listener=input_listener
    #             )
    #         except grpc._channel._MultiThreadedRendezvous:
    #             logging.debug("Generating new 'input_listener'")
    #         except Exception as ex:
    #             logging.exception("Raised an exception in 'get_input_listener': %s", ex)

    # # Start receiving Input messages
    # Thread(target=get_input_listener, args=[iotics_api]).start()


if __name__ == "__main__":
    main()
