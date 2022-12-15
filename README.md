# IOTICS Tutorials in Python

This repository includes everything you need to know to get started with IOTICS from the very basic Digital Twins operations to more advanced applications.
If you haven't done it already, you might want to take a quick look at what [IOTICS](https://docs.iotics.com/) is and our overview of the [IOTICS Digital Twins](https://docs.iotics.com/docs/digital-twins).

## Repository Structure

The repository is divided into the following subfolders:
- __getting_started__ (coming soon): contains a set of tutorials focused on the basic IOTICS operations implemented with REST + STOMP and the gRPC Python Client Library;
- __examples__: contains more advanced and complete applications implemented with the gRPC Python Client Library.

## Setup

To run the code in this repository you first need to:
1.  Install [Python](https://www.python.org/downloads/) (3.7+) on your machine;
2.  Create a new Python virtual environment:
    ```bash
    ON LINUX:
    python3 -m venv iotics_tutorials
    ON WINDOWS:
    python -m venv iotics_tutorials
    ```
3.  Activate the virtual environment:
    ```bash
    ON LINUX:
    source iotics_tutorials/bin/activate
    ON WINDOWS:
    .\iotics_tutorials\Scripts\Activate.bat
    ON WINDOWS (powershell):
    .\iotics_tutorials\Scripts\Activate.ps1
    ```
4.  Download the IOTICS Stomp Library from [this](https://github.com/Iotic-Labs/iotics-host-lib/blob/master/stomp-client/iotic.web.stomp-1.0.6.tar.gz) link to the root folder of this repository;
5.  Install the required dependencies: `pip install -r requirements.txt`
6.  Set up required environment variables or create an `.env` file with the following values to be used to run any code in this repository:
    -   `HOST` - Domain name of the IOTICSpace with which to communicate
    -   `USER_KEY_NAME` - Key Name of the User Identity
    -   `USER_SEED` - Seed of the User Identity
    -   `AGENT_KEY_NAME` = Key Name of the Agent Identity
    -   `AGENT_SEED` - Seed of the Agent Identity
    -   `TOKEN_DURATION` -  How long in seconds the auth tokens will last (30 seconds if not specified)
