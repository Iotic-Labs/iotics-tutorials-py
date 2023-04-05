# IOTICS Getting Started

This folder contains an ordered list of examples implemented with REST (`*_rest.py`), STOMP (`*_stomp.py`) and the gRPC Python Client Library (`*_grpc.py`) focused on getting started with IOTICS.

## 1. Generate New Seed

It shows the usage of the Identity Library for the simple generation of a Seed. The latter, along with a Key Name (see `create_user_and_agent.py`), can be used for the creation of *Registered Identities* (Users, Agents and Twins).

## 2. Create User and Agent

It allows the creation (or retrieval) of a User and an Agent Identity through the use of the Identity Library (High Level). This section will be the entry point of any IOTICS application.

## 3. Twin Publisher

A Twin Publisher is a Twin that periodically shares data into IOTICS via one or more Feeds. The Feed's data will always be publicly accessible by any Twin in the same Space. The same Feed's data can also be accessible to Twins belonging to other Spaces according to the concept of Selective Data Sharing.

## 4. Twin Follower (COMING SOON)

A Twin Follower is a Twin that subscribes to a Twin Publisher's Feed(s) to receive data.

## 5. Twin Receiver (COMING SOON)

A Twin Receiver is a Twin that waits for Input messages. The Twin Receiver can have one or more Inputs from which to receive messages. Input Messages are generally used to control or trigger some actions on the Twin Receiver. The Input on the Twin Receiver will always be available from any Twin in the same Space. The same Input can also be available from Twins belonging to other Spaces according to the concept of Selective Data Sharing.

## 6. Twin Sender (COMING SOON)

A Twin Sender is a Twin that sends Input messages to another Twin's Input.

## 7. Twin Model (COMING SOON)

A Twin Model is a Twin that serves as a template for other Twins. It must include a specific Twin Property for it to be classified as a Twin Model. Although this type of Twin can include one or more Feeds and/or Inputs, it should not incorporate any behaviour (logic): publish/follow/send/receive.

## 8. Twin from Model (COMING SOON)

A Twin from Model is a Twin that replicates the structure (Properties, Feed(s) and Input(s)) of a Twin Model. It must include a specific Twin Property for it to be classified as a Twin from Model. This type of Twin can incorporate a behaviour: publish/follow/send/receive.