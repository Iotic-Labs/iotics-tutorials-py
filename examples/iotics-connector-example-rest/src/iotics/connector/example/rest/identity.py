import logging
import sys
from datetime import datetime, timedelta
from time import sleep, time
from typing import List, Optional

from constants import TOKEN_REFRESH_PERIOD_PERCENT
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)
from rest_client import RestClient
from stomp_client import StompClient


class Identity:
    def __init__(
        self,
        resolver_url: str,
        user_key_name: str,
        user_seed: str,
        agent_key_name: str,
        agent_seed: str,
        token_duration: int = 30,
    ):
        self._user_key_name: str = user_key_name
        self._user_seed: bytes = bytes.fromhex(user_seed)
        self._agent_key_name: str = agent_key_name
        self._agent_seed: bytes = bytes.fromhex(agent_seed)
        self._token_duration: int = token_duration

        self._high_level_identity_api: HighLevelIdentityApi = None
        self._user_identity: RegisteredIdentity = None
        self._agent_identity: RegisteredIdentity = None
        self._token: str = None
        self._token_last_updated: float = None

        self._setup(resolver_url=resolver_url)

    @staticmethod
    def _check_global_var(var, var_name: str):
        if not var:
            logging.error("Parameter %s not set", var_name)
            sys.exit(1)

    def _setup(self, resolver_url: str):
        self._check_global_var(var=self._user_key_name, var_name="USER_KEY_NAME")
        self._check_global_var(var=self._user_seed, var_name="USER_SEED")
        self._check_global_var(var=self._agent_key_name, var_name="AGENT_KEY_NAME")
        self._check_global_var(var=self._agent_seed, var_name="AGENT_SEED")

        self._high_level_identity_api = get_rest_high_level_identity_api(
            resolver_url=resolver_url
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
        return int(self._token_duration)

    def get_token(self) -> str:
        return self._token

    def refresh_token(self):
        self._token: str = self._high_level_identity_api.create_agent_auth_token(
            agent_registered_identity=self._agent_identity,
            user_did=self._user_identity.did,
            duration=self._token_duration,
        )
        self._token_last_updated = time()

        logging.debug(
            "New token generated. Expires at %s",
            datetime.now() + timedelta(seconds=self._token_duration),
        )

    def create_twin_with_control_delegation(
        self, twin_key_name: str, twin_seed: Optional[str] = None
    ) -> RegisteredIdentity:
        twin_seed_bytes: bytes
        if not twin_seed:
            twin_seed_bytes = self._agent_seed
        else:
            twin_seed_bytes = bytes.fromhex(twin_seed)

        twin_identity: RegisteredIdentity = (
            self._high_level_identity_api.create_twin_with_control_delegation(
                twin_seed=twin_seed_bytes,
                twin_key_name=twin_key_name,
                agent_registered_identity=self._agent_identity,
            )
        )

        logging.debug(
            "Twin Identity %s created with Control delegation", twin_identity.did
        )

        return twin_identity


def auto_refresh_token(
    identity: Identity,
    rest_client: RestClient,
    stomp_client_list: List[StompClient] = [],
):
    token_period = int(identity.token_duration * TOKEN_REFRESH_PERIOD_PERCENT)

    while True:
        start_processing_time = time()

        identity.refresh_token()
        rest_client.new_token(token=identity.get_token())
        for stomp_client in stomp_client_list:
            stomp_client.new_token(token=identity.get_token())

        sleep(token_period - (time() - start_processing_time))
