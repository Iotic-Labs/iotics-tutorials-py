# IOTICS Tutorials in Python

This repository includes everything you need to know to get started with IOTICS from the very basic Digital Twins operations to more advanced applications.
If you haven't done it already, you might want to take a quick look at what [IOTICS](https://docs.iotics.com/) is and our overview of the [IOTICS Digital Twins](https://docs.iotics.com/docs/digital-twins).

## Repository Structure

The repository is divided into the following subfolders:
- __getting_started__ (WIP): contains a set of tutorials focused on the basic IOTICS operations;
- __examples__: contains more advanced and complete applications.

## Setup

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

Last step is to set up your Space URL along with your credentials on top of the example code you want to execute with the following values:
- `HOST_URL` - Domain name of the IOTICSpace with which to communicate. E.g. `HOST_URL=https://uk-metoffice.iotics.space`
- `USER_KEY_NAME` - Key Name of the User Identity
- `USER_SEED` - Seed of the User Identity
- `AGENT_KEY_NAME` - Key Name of the Agent Identity
- `AGENT_SEED` - Seed of the Agent Identity

