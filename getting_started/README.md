# IOTICS Getting Started

This folder contains an ordered list of examples implemented with REST (`*_rest.py`) and the gRPC Python Client Library (`*_grpc.py`) focused on getting started with IOTICS. The idea is to go through these exercises in the order indicated so you can understand how to use IOTICS from the easier examples to the most complicated ones.

## Example Description

### 1. Generate New Seed

It shows the usage of the Identity Library for the simple generation of a Seed. The latter, along with a Key Name (see `create_user_and_agent.py`), can be used for the creation of *Registered Identities* (Users, Agents and Twins).

### 2. Create User and Agent

It allows the creation (or retrieval) of a User and an Agent Identity through the use of the Identity Library (High Level). This section will be the entry point of any IOTICS application.

### 3. Twin Publisher

A Twin Publisher is a Twin that periodically shares data into IOTICS via one or more Feeds. The Feed's data will always be publicly accessible by any Twin in the same Space. The same Feed's data can also be accessible to Twins belonging to other Spaces according to the concept of Selective Data Sharing.

### 4. Search Twins

An example of the Search Twin operation is provided to find the Twin Publisher created in the previous exercise.

### 5. Twin Follower

A Twin Follower is a Twin that subscribes to a Twin Publisher's Feed(s) to receive data.

### 6. Twin Receiver

A Twin Receiver is a Twin that waits for Input messages. The Twin Receiver can have one or more Inputs from which to receive messages. Input Messages are generally used to control or trigger some actions on the Twin Receiver. The Input on the Twin Receiver will always be available from any Twin in the same Space. The same Input can also be available from Twins belonging to other Spaces according to the concept of Selective Data Sharing.

### 7. Twin Sender

A Twin Sender is a Twin that sends Input messages to another Twin's Input.

### 8. Twin Synthesiser

A Twin Synthesiser is a Twin that:
1. receives data from 1 or more Twin's Feeds;
2. synthesises the data received (performs some sort of computation on the data);
3. publishes the synthesised data back to IOTICS via one or more Feeds.

### 9. Twin Model

A Twin Model is a Twin that serves as a template for other Twins. It must include a specific Twin Property to be classified as a Twin Model. Although this type of Twin can include one or more Feeds and/or Inputs, it should not incorporate any behaviour (logic): publish/follow/send/receive.

### 10. Twins from Model

A Twin from Model is a Twin that replicates the structure (Properties, Feed(s) and Input(s)) of a Twin Model. It must include a specific Twin Property for it to be classified as a Twin from Model. This type of Twin can incorporate a behaviour: publish/follow/send/receive.

### 11. Twin Shadow

Twins Shadow are Twins that virtualise other Twins. They are generally used to:
-   provide a stub or a simulation of an existing Twin;
-   throttle or anonymise the data published;
-   to partition security and access control to feeds and Metadata selectively.

## Set-up

To run any of the examples, you first need to create and activate your Python virtual environment. E.g.:
```bash
make setup
source ./iotics_tutorials/bin/activate
```

Alternatively you can follow the manual steps below:

1.  Create a new Python virtual environment:
    - Linux: `python3 -m venv iotics_tutorials`
    - Windows: `python -m venv iotics_tutorials`

2.  Activate the virtual environment:
    - Linux: `source ./iotics_tutorials/bin/activate`
    - Windows: `.\iotics_tutorials\Scripts\Activate.bat`
    - Windows (powershell): `.\iotics_tutorials\Scripts\Activate.ps1`

3.  Download the IOTICS Stomp Library from [this](https://github.com/Iotic-Labs/iotics-host-lib/blob/master/stomp-client/iotic.web.stomp-1.0.6.tar.gz) link to the root folder of this repository;
4.  Install the required dependencies: `pip install -r requirements.txt`
