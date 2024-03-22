SHELL := /bin/bash
VENV_PATH ?= ./iotics_tutorials
STOMP_LIBRARY="https://github.com/Iotic-Labs/iotics-host-lib/raw/master/stomp-client/iotic.web.stomp-1.0.6.tar.gz"

ifeq ($(OS),Windows_NT)
  VENV_PATH_DIR=Scripts
else
  VENV_PATH_DIR=bin
endif

setup:
	python3 -m venv $(VENV_PATH)
	wget $(STOMP_LIBRARY)
	source "$(VENV_PATH)"/"$(VENV_PATH_DIR)"/activate \
	&& pip install -r requirements.txt
