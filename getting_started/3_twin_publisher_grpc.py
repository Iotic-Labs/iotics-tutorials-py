"""This script aims to show how to implement a Twin Publisher
that shares a random integer every 5 seconds via the gRPC Python Client library.
"""
from random import randint
from time import sleep
from typing import Optional

import requests
from iotics.lib.grpc.auth import AuthInterface
from iotics.lib.grpc.helpers import create_feed_with_meta, create_property, create_value
from iotics.lib.grpc.iotics_api import IoticsApi
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)

HOST_URL: str = ""  # URL of your IOTICSpace (i.e.: "https://my-space.iotics.space")

# In order to create the following values, you can look at "2_create_user_and_agent.py".
USER_KEY_NAME: str = ""
USER_SEED: str = ""
AGENT_KEY_NAME: str = ""
AGENT_SEED: str = ""


class Identity(AuthInterface):
    """The gRPC Python Client Library requires an instance of an Identity Class
    that inherits the "AuthInterface" Class. The latter defines 3 methods that need to be
    implemented in the former:
    - 'get_host': needs to return the gRPC endpoint;
    - 'get_token': needs to return a valid IOTICS token;
    - 'refresh_token': needs to generate a new IOTICS token.
    We are going to add some additional methods to this Class so we can easily:
    1. create (or retrieve) User and Agent Identities;
    2. create (or retrieve) Twin Identities.
    """

    def __init__(self):
        self._grpc_endpoint: str = None
        self._user_key_name: str = USER_KEY_NAME
        self._user_seed: bytes = bytes.fromhex(USER_SEED)
        self._agent_key_name: str = AGENT_KEY_NAME
        self._agent_seed: bytes = bytes.fromhex(AGENT_SEED)

        self._high_level_identity_api: HighLevelIdentityApi = None
        self._user_identity: RegisteredIdentity = None
        self._agent_identity: RegisteredIdentity = None
        self._token: str = None

        self._setup()

    def _setup(self):
        # "index_json" is the IOTICS path that redirects to the index.json.
        # The latter includes some of the parameters that have to be used
        # in a usual IOTICS application (such as "resolver, "grpc", etc.)
        index_json: str = HOST_URL + "/index.json"
        response: requests.Response = requests.get(
            url=index_json, headers={"accept": "application/json"}
        ).json()
        self._grpc_endpoint: str = response["grpc"]
        resolver_url: str = response["resolver"]

        self._high_level_identity_api: HighLevelIdentityApi = (
            get_rest_high_level_identity_api(resolver_url=resolver_url)
        )
        (
            self._user_identity,
            self._agent_identity,
        ) = self._high_level_identity_api.create_user_and_agent_with_auth_delegation(
            user_seed=self._user_seed,
            user_key_name=self._user_key_name,
            agent_seed=self._agent_seed,
            agent_key_name=self._agent_key_name,
        )

        # Any IOTICS operation requires a token (JWT). The latter can be created using:
        # 1. A User DID;
        # 2. An Agent Identity;
        # 3. A duration (in seconds)
        # This token will only be valid for the duration expressed on point 3 above.
        # When the token expires you won't be able to use the API so you need to generate a new token.
        # Please remember that the longer the token's duration, the less secure your Twins are.
        # (The token may be stolen and a malicious user can use your Twins on your behalf).
        self.refresh_token()

    def get_host(self) -> str:
        """This method is part of the "AuthInterface" class."""
        return self._grpc_endpoint

    def get_token(self) -> str:
        """This method is part of the "AuthInterface" class."""
        return self._token

    def refresh_token(self):
        """This method is part of the "AuthInterface" class."""
        self._token = self._high_level_identity_api.create_agent_auth_token(
            agent_registered_identity=self._agent_identity,
            user_did=self._user_identity.did,
            duration=60,
        )

    def create_twin_with_control_delegation(
        self, twin_key_name: str, twin_seed: Optional[str] = None
    ) -> RegisteredIdentity:
        """This method will use the 'create_twin_with_control_delegation' method of the
        Identity Library so we can create (or retrieve) a Twin Identity.
        As any other Identity, a Twin Identity can be created with a Key Name and a Seed.
        Regarding the latter it is a best-practice to re-use the 'AGENT_SEED'.
        """

        twin_seed_bytes: bytes
        if not twin_seed:
            twin_seed_bytes = self._agent_seed
        else:
            twin_seed_bytes = bytes.fromhex(twin_seed)

        twin_registered_identity: RegisteredIdentity = self._high_level_identity_api.create_twin_with_control_delegation(
            # The Twin Key Name's concept is the same as Agent and User Key Name
            twin_key_name=twin_key_name,
            twin_seed=twin_seed_bytes,
            agent_registered_identity=self._agent_identity,
        )

        return twin_registered_identity


def main():
    identity_api = Identity()
    iotics_api = IoticsApi(auth=identity_api)

    # We need to create a new Twin Identity which will be used for our Twin Publisher.
    # Only Agents can perform actions against a Twin.
    # This means, after creating the Twin Identity it has to "control-delegate" an Agent Identity
    # so the latter can control the Digital Twin.
    twin_publisher_identity: RegisteredIdentity = (
        identity_api.create_twin_with_control_delegation(twin_key_name="TwinPublisher")
    )

    twin_publisher_did: str = twin_publisher_identity.did

    feed_id: str = "temperature"
    value_label: str = "reading"
    iotics_api.upsert_twin(
        twin_did=twin_publisher_did,
        properties=[
            create_property(
                key="http://www.w3.org/2000/01/rdf-schema#label",
                value="Twin Publisher",
                language="en",
            )
        ],
        feeds=[
            create_feed_with_meta(
                feed_id=feed_id,
                properties=[
                    create_property(
                        key="http://www.w3.org/2000/01/rdf-schema#label",
                        value="Temperature",
                        language="en",
                    )
                ],
                values=[
                    create_value(
                        label=value_label,
                        comment="Temperature in degrees Celsius",
                        data_type="integer",
                        unit="http://qudt.org/vocab/unit/DEG_C",
                    )
                ],
            )
        ],
    )

    print(f"Twin {twin_publisher_did} upserted succesfully")

    try:
        while True:
            rand_temperature: int = randint(
                0, 30
            )  # Generate a random integer from 0 to 30
            # The data needs to be prepared as a dictionary where all the keys have to reflect the values' label
            data_to_share: dict = {value_label: rand_temperature}
            # Next step is to use the "share_feed_data" method
            # (the convertion into JSON and encoding using base64 will happen automatically)
            iotics_api.share_feed_data(
                twin_did=twin_publisher_did, feed_id=feed_id, data=data_to_share
            )

            print(
                f"Shared {data_to_share} from Twin {twin_publisher_did} via Feed {feed_id}"
            )

            sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
