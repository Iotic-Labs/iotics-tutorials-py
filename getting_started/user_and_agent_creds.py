from iotics.lib.identity.api.regular_api import get_rest_identity_api

# The Resolver URL can be found in <spaceurl>/index.json
identity_api = get_rest_identity_api(resolver_url="resolver_url")

"""A new Identity, be it a User, an Agent or a Twin can be created with:
1.  A Key Name: a string of characters that uniquely identifies the entity;
2.  A Seed: a random string of characters generated via the API;
3.  A Name (optional): a human-friendly string of characters that represents the entity
"""

user_seed = identity_api.create_seed()  # Generate a new seed
user_key_name = (
    "UserBob"  # Can be anything as long as it uniquely identifies you as a User
)
user_name = "#user-0"  # Using default value

# Use the "create_user_identity" operation to create the User Identity
user_identity = identity_api.create_user_identity(
    user_key_name=user_key_name, user_seed=user_seed, user_name="#user-0"
)

agent_seed = identity_api.create_seed()  # Generate a new seed
agent_key_name = "Agent1"  # Can be anything as long as it uniquely identifies an Agent executing operations
agent_name = "#agent-0"  # Using default value

# Use the "create_agent_identity" operation to create the Agent Identity
agent_identity = identity_api.create_agent_identity(
    agent_key_name=agent_key_name, agent_seed=agent_seed, agent_name=agent_name
)

"""Make sure you store the following credentials in a safe place
as they will be used any time you want to use the API.
If you lose them you will not be able to interact with your twins anymore.
"""

print("STORE CREDENTIALS !")
print("USER_SEED:", user_seed.hex())
print("USER_KEY_NAME:", user_key_name)
print("AGENT_SEED:", agent_seed.hex())
print("AGENT_KEY_NAME:", agent_key_name)

"""After the above steps a User and an Agent Identity have been created.
In IOTICS, Agents (and not Users) create and update Digital Twins.
Therefore it is important that you as the User (or the application that acts as the User)
authorise the Agent to work on the User's behalf."""

identity_api.user_delegates_authentication_to_agent(
    user_registered_identity=user_identity, agent_registered_identity=agent_identity
)
