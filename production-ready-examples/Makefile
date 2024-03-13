V = 0
Q = $(if $(filter 1,$V),,@)

ifeq ($(OS),Windows_NT)
  VENV_PATH_DIR = Scripts
else
  VENV_PATH_DIR = bin
endif

.PHONY: example-publisher-run example-follower-run example-run-all example-down

example-publisher-run:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build publisher

example-follower-run:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build follower

example-run-all:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build

example-down:
	$(Q) docker-compose -f docker/docker-compose.yaml down
