import logging
import random
import sys
import threading
from time import sleep

from helpers import (
    PROPERTY_KEY_COLOR,
    PROPERTY_KEY_COMMENT,
    PROPERTY_KEY_CREATED_BY,
    PROPERTY_KEY_FROM_MODEL,
    PROPERTY_KEY_HOST_ALLOW_LIST,
    PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
    PROPERTY_KEY_LABEL,
    PROPERTY_KEY_SPACE_NAME,
    PROPERTY_KEY_TYPE,
    PROPERTY_VALUE_ALLOW_ALL,
    PROPERTY_VALUE_MODEL,
    UNIT_DEGREE_CELSIUS,
    auto_refresh_token,
)
from identity import Identity
from iotics.lib.grpc.helpers import (
    create_feed_with_meta,
    create_location,
    create_property,
    create_value,
)
from iotics.lib.grpc.iotics_api import IoticsApi as IOTICSviagRPC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)


def main():
    identity = Identity()
    iotics_api = IOTICSviagRPC(auth=identity)

    threading.Thread(
        target=auto_refresh_token,
        args=(
            identity,
            iotics_api,
        ),
        daemon=True,
    ).start()

    publisher_model_twin_identity = identity.create_twin_with_control_delegation(
        twin_key_name="SensorTwinModel"
    )
    publisher_model_twin_did = publisher_model_twin_identity.did
    iotics_api.upsert_twin(
        twin_did=publisher_model_twin_did,
        properties=[
            create_property(
                key=PROPERTY_KEY_TYPE, value=PROPERTY_VALUE_MODEL, is_uri=True
            ),
            create_property(
                key=PROPERTY_KEY_LABEL,
                value="Temperature Sensor Model",
                language="en",
            ),
            create_property(
                key=PROPERTY_KEY_COMMENT,
                value="Model of a Temperature Sensor Twin",
                language="en",
            ),
            create_property(
                key=PROPERTY_KEY_SPACE_NAME, value="Replace with Space Name"
            ),
            create_property(key=PROPERTY_KEY_COLOR, value="#9aceff"),
            create_property(
                key=PROPERTY_KEY_CREATED_BY, value="Replace with your Name"
            ),
            create_property(
                key="https://data.iotics.com/app#defines",
                value="https://saref.etsi.org/core/TemperatureSensor",
                is_uri=True,
            ),
            create_property(
                key="https://saref.etsi.org/core/hasModel", value="SET-LATER"
            ),
        ],
        feeds=[
            create_feed_with_meta(
                feed_id="temperature",
                properties=[
                    create_property(
                        key=PROPERTY_KEY_LABEL, value="Temperature", language="en"
                    ),
                    create_property(
                        key=PROPERTY_KEY_COMMENT,
                        value="Current Temperature of a room",
                        language="en",
                    ),
                ],
                values=[
                    create_value(
                        label="reading",
                        comment="Temperature in degrees Celsius",
                        unit=UNIT_DEGREE_CELSIUS,
                        data_type="integer",
                    )
                ],
            )
        ],
    )

    room_number_to_twin_did = {}
    for room_number in range(3):
        publisher_twin_identity = identity.create_twin_with_control_delegation(
            twin_key_name=f"SensorTwin{room_number}"
        )
        publisher_twin_did = publisher_twin_identity.did

        iotics_api.upsert_twin(
            twin_did=publisher_twin_did,
            properties=[
                create_property(
                    key=PROPERTY_KEY_FROM_MODEL,
                    value=publisher_model_twin_did,
                    is_uri=True,
                ),
                create_property(
                    key=PROPERTY_KEY_LABEL,
                    value=f"Temperature Sensor Twin {room_number+1}",
                    language="en",
                ),
                create_property(
                    key=PROPERTY_KEY_COMMENT,
                    value=f"Temperature Sensor Twin of Room {room_number+1}",
                    language="en",
                ),
                create_property(
                    key=PROPERTY_KEY_SPACE_NAME, value="Replace with Space Name"
                ),
                create_property(key=PROPERTY_KEY_COLOR, value="#9aceff"),
                create_property(
                    key=PROPERTY_KEY_CREATED_BY, value="Replace with your Name"
                ),
                create_property(
                    key=PROPERTY_KEY_HOST_METADATA_ALLOW_LIST,
                    value=PROPERTY_VALUE_ALLOW_ALL,
                    is_uri=True,
                ),
                create_property(
                    key=PROPERTY_KEY_HOST_ALLOW_LIST,
                    value=PROPERTY_VALUE_ALLOW_ALL,
                    is_uri=True,
                ),
                create_property(
                    key="https://data.iotics.com/app#defines",
                    value="https://saref.etsi.org/core/TemperatureSensor",
                    is_uri=True,
                ),
                create_property(
                    key="https://saref.etsi.org/core/hasModel", value="T1234"
                ),
            ],
            feeds=[
                create_feed_with_meta(
                    feed_id="temperature",
                    properties=[
                        create_property(
                            key=PROPERTY_KEY_LABEL,
                            value="Temperature",
                            language="en",
                        ),
                        create_property(
                            key=PROPERTY_KEY_COMMENT,
                            value="Current Temperature of a room",
                            language="en",
                        ),
                    ],
                    values=[
                        create_value(
                            label="reading",
                            comment="Temperature in degrees Celsius",
                            unit=UNIT_DEGREE_CELSIUS,
                            data_type="integer",
                        )
                    ],
                )
            ],
            location=create_location(lat=51.5, lon=-0.1),
        )

        room_number_to_twin_did.update({room_number: publisher_twin_did})

    try:
        while True:
            rand_temp_list = random.sample(range(10, 31), len(room_number_to_twin_did))
            for room_number, rand_temp in enumerate(rand_temp_list):
                iotics_api.share_feed_data(
                    twin_did=room_number_to_twin_did[room_number],
                    feed_id="temperature",
                    data={"reading": rand_temp},
                )
                logging.info(
                    f"Shared temperature {rand_temp} from Twin {room_number_to_twin_did[room_number]}"
                )

            sleep(3)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
