import logging
import os
import sys
from datetime import datetime, timedelta
from time import time

import dotenv
import requests
from iotics.lib.grpc.auth import AuthInterface
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)

dotenv.load_dotenv()
HOST = os.environ["HOST"]
USER_KEY_NAME = os.environ["USER_KEY_NAME"]
USER_SEED = bytes.fromhex(os.environ["USER_SEED"])
AGENT_KEY_NAME = os.environ["AGENT_KEY_NAME"]
AGENT_SEED = bytes.fromhex(os.environ["AGENT_SEED"])
TOKEN_DURATION = int(os.getenv("TOKEN_DURATION", 30))


class Identity(AuthInterface):
    def __init__(self):
        self._high_level_identity_api: HighLevelIdentityApi = None
        self._user_identity: RegisteredIdentity = None
        self._agent_identity: RegisteredIdentity = None
        self._host_url: str = None
        self._token_duration: int = None
        self._token: str = None
        self._token_last_updated: float = None
        self._setup()

    def _setup(self):
        host_url = HOST
        split_url = host_url.partition("://")
        space = split_url[2] or split_url[0]
        self._host_url = space + ":10001"
        index_json = f"{host_url}/index.json"
        resolver_url = requests.get(index_json).json()["resolver"]
        self._high_level_identity_api = get_rest_high_level_identity_api(
            resolver_url=resolver_url
        )
        (
            self._user_identity,
            self._agent_identity,
        ) = self._high_level_identity_api.create_user_and_agent_with_auth_delegation(
            user_seed=USER_SEED,
            user_key_name=USER_KEY_NAME,
            agent_seed=AGENT_SEED,
            agent_key_name=AGENT_KEY_NAME,
        )
        self._token_duration = TOKEN_DURATION
        self.refresh_token()

    @property
    def user_identity(self) -> RegisteredIdentity:
        return self._user_identity

    @property
    def agent_identity(self) -> RegisteredIdentity:
        return self._agent_identity

    @property
    def token_last_updated(self) -> int:
        return self._token_last_updated

    @property
    def token_duration(self) -> int:
        return self._token_duration

    def get_host(self) -> str:
        return self._host_url

    def get_token(self) -> str:
        return self._token

    def refresh_token(self):
        self._token = self._high_level_identity_api.create_agent_auth_token(
            agent_registered_identity=self._agent_identity,
            user_did=self._user_identity.did,
            duration=self._token_duration,
        )

        logging.debug(
            f"New token generated. Expires at {datetime.now() + timedelta(seconds=self._token_duration)}"
        )

        self._token_last_updated = time()

    def create_twin_with_control_delegation(
        self, twin_key_name: str, twin_seed: str = None
    ) -> RegisteredIdentity:
        if not twin_seed:
            twin_seed = AGENT_SEED

        twin_identity = (
            self._high_level_identity_api.create_twin_with_control_delegation(
                twin_seed=twin_seed,
                twin_key_name=twin_key_name,
                agent_registered_identity=self._agent_identity,
            )
        )

        logging.info(
            f"Twin Identity {twin_identity.did} created with Control delegation"
        )

        return twin_identity
