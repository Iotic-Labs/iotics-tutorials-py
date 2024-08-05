V = 0
Q = $(if $(filter 1,$V),,@)

ifeq ($(OS),Windows_NT)
  VENV_PATH_DIR = Scripts
else
  VENV_PATH_DIR = bin
endif

DOCKER_COMPOSE = docker compose -f docker/docker-compose.yaml

define DOCKER_TARGET
example-$(1)-run:
	$(Q) $(DOCKER_COMPOSE) up --build $(1)

example-$(1)-run-detached:
	$(Q) $(DOCKER_COMPOSE) up --build $(1) -d

example-$(1)-logs:
	$(Q) $(DOCKER_COMPOSE) logs $(1) -f

example-$(1)-down:
	$(Q) $(DOCKER_COMPOSE) down $(1)
endef

$(foreach service,publisher historian_writer synthesiser databypass historian_reader,$(eval $(call DOCKER_TARGET,$(service))))

example-all-run:
	$(Q) $(DOCKER_COMPOSE) up --build

example-all-down:
	$(Q) $(DOCKER_COMPOSE) down
