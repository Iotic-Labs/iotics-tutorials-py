import logging
import sys
from datetime import datetime, timedelta
from time import time

from iotics.lib.grpc.auth import AuthInterface
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
    get_rest_high_level_identity_api,
)

log = logging.getLogger(__name__)


class Identity(AuthInterface):
    def __init__(
        self,
        resolver_url: str,
        grpc_endpoint: str,
        user_key_name: str,
        user_seed: str,
        agent_key_name: str,
        agent_seed: str,
        token_duration: int = 60,
    ):
        self._resolver_url: str = resolver_url
        self._grpc_endpoint: str = grpc_endpoint
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

        self._initialise()

    @staticmethod
    def _check_global_var(var, var_name: str):
        if not var:
            logging.error("Parameter %s not set", var_name)
            sys.exit(1)

    def _initialise(self):
        """Check all the env variables have been set properly.
        Then create/retrieve a User and an Agent Identity with auth delegation,
        followed by the generation of a new IOTICS token.
        """

        log.debug("Initialising Identity...")
        self._check_global_var(var=self._user_key_name, var_name="USER_KEY_NAME")
        self._check_global_var(var=self._user_seed, var_name="USER_SEED")
        self._check_global_var(var=self._agent_key_name, var_name="AGENT_KEY_NAME")
        self._check_global_var(var=self._agent_seed, var_name="AGENT_SEED")

        self._high_level_identity_api = get_rest_high_level_identity_api(
            resolver_url=self._resolver_url
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

        log.debug("User and Agent created with auth delegation")

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

    def get_host(self) -> str:
        return self._grpc_endpoint

    def get_token(self) -> str:
        return self._token

    def refresh_token(self):
        """Generate a new IOTICS token that can be used to execute IOTICS operations.
        Update 'token_last_updated' so the auto refresh token mechanism
        is aware of when to generate a new token.
        """

        self._token: str = self._high_level_identity_api.create_agent_auth_token(
            agent_registered_identity=self._agent_identity,
            user_did=self._user_identity.did,
            duration=self._token_duration,
        )
        self._token_last_updated = time()

        log.debug(
            "New token generated. Expires at %s",
            datetime.now() + timedelta(seconds=self._token_duration),
        )

    def create_twin_with_control_delegation(
        self, twin_key_name: str, twin_seed: str = None
    ) -> RegisteredIdentity:
        """Wrapper of the 'create_twin_with_control_delegation' function
        of the High Level Identity API. This will help creating new Twin Identities
        with control delegation against the Agent Identity of this class.

        Args:
            twin_key_name (str): key name of the Twin Identity to be created.
            twin_seed (str, optional): twin seed of the Twin Identity.
                Defaults to the Agent's Seed if not provided.

        Returns:
            RegisteredIdentity: an object of a Twin Registered Identity.
        """

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

        log.debug("Twin Identity %s created with Control delegation", twin_identity.did)

        return twin_identity
