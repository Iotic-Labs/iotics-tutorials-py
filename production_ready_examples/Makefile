V = 0
Q = $(if $(filter 1,$V),,@)

ifeq ($(OS),Windows_NT)
  VENV_PATH_DIR = Scripts
else
  VENV_PATH_DIR = bin
endif

SERVICES = publisher follower synthesiser databypass historian_reader

define SERVICE_COMMANDS
example-run $(1):
	$(Q) docker-compose -f docker/docker-compose.yaml up --build $(1)

example-run-detached $(1):
	$(Q) docker-compose -f docker/docker-compose.yaml up --build $(1) -d

example-logs $(1):
	$(Q) docker-compose -f docker/docker-compose.yaml logs $(1) -f

example-down $(1):
	$(Q) docker-compose -f docker/docker-compose.yaml down $(1)
endef

# Generate rules for each service
$(foreach service,$(SERVICES),$(eval $(call SERVICE_COMMANDS,$(service))))
