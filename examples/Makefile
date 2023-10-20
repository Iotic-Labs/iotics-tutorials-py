V = 0
Q = $(if $(filter 1,$V),,@)

ifeq ($(OS),Windows_NT)
  VENV_PATH_DIR = Scripts
else
  VENV_PATH_DIR = bin
endif

.PHONY: example-run example-down

example-run:
	$(Q) docker-compose -f docker/docker-compose.yaml up --build

example-down:
	$(Q) docker-compose -f docker/docker-compose.yaml down
