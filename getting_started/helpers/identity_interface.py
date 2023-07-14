"""The gRPC Python Client Library requires an instance of an Identity Class
that inherits the "AuthInterface" Class. The latter defines 3 methods that need to be
implemented in the former:
- 'get_host': needs to return the gRPC endpoint;
- 'get_token': needs to return a valid IOTICS token;
- 'refresh_token': needs to generate a new IOTICS token.
"""

from iotics.lib.grpc.auth import AuthInterface
from iotics.lib.identity.api.high_level_api import (
    HighLevelIdentityApi,
    RegisteredIdentity,
)


class IdentityInterface(AuthInterface):
    def __init__(self, grpc_endpoint: str, identity_api: HighLevelIdentityApi):
        self._grpc_endpoint: str = grpc_endpoint
        self._token: str = None
        self._high_level_identity_api: HighLevelIdentityApi = identity_api

    def get_host(self) -> str:
        """This method is part of the "AuthInterface" class."""
        return self._grpc_endpoint

    def get_token(self) -> str:
        """This method is part of the "AuthInterface" class."""
        return self._token

    def refresh_token(
        self,
        user_identity: RegisteredIdentity,
        agent_identity: RegisteredIdentity,
        token_duration: int = 60,
    ):
        """This method is part of the "AuthInterface" class."""
        self._token = self._high_level_identity_api.create_agent_auth_token(
            agent_registered_identity=agent_identity,
            user_did=user_identity.did,
            duration=token_duration,
        )
