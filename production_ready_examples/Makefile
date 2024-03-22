V = 0
Q = $(if $(filter 1,$V),,@)

ifeq ($(OS),Windows_NT)
  VENV_PATH_DIR = Scripts
else
  VENV_PATH_DIR = bin
endif

example-publisher-run:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build publisher

example-publisher-run-detached:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build publisher -d

example-publisher-logs:
	$(Q) docker-compose -f docker/docker-compose.yaml logs publisher -f

example-publisher-down:
	$(Q) docker-compose -f docker/docker-compose.yaml down publisher

example-follower-run:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build follower

example-follower-run-detached:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build follower -d

example-follower-logs:
	$(Q) docker-compose -f docker/docker-compose.yaml logs follower -f

example-follower-down:
	$(Q) docker-compose -f docker/docker-compose.yaml down follower

example-all-run:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build

example-all-down:
	$(Q) docker-compose -f docker/docker-compose.yaml down
