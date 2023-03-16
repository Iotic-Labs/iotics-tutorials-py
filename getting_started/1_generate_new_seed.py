import sys

from iotics.lib.identity.api.high_level_api import (
    get_rest_high_level_identity_api,
    HighLevelIdentityApi,
)

RESOLVER_URL: str = ""  # You can find it at <space_url>/index.json --> "resolver"


def main():
    if not RESOLVER_URL:
        print("Please add the RESOLVER_URL to this script.")
        print('You can find it at <space_url>/index.json --> "resolver"')
        sys.exit(1)

    identity_api: HighLevelIdentityApi = get_rest_high_level_identity_api(
        resolver_url=RESOLVER_URL
    )

    # The seed generated is a 'bytes' object
    bytes_seed: bytes = identity_api.create_seed()

    # In order to print it in a human-readable format we can use the built-in function "hex()"
    # which converts it to an hexadecimal string
    hex_string_seed: str = bytes_seed.hex()

    print("SEED:", hex_string_seed)


if __name__ == "__main__":
    main()
