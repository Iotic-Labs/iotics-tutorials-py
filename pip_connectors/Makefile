V = 0
Q = $(if $(filter 1,$V),,@)

ifeq ($(OS),Windows_NT)
  VENV_PATH_DIR = Scripts
else
  VENV_PATH_DIR = bin
endif

pip-vesselmovement-run:
	$(Q) docker compose -f docker/docker-compose.yaml up --build vesselmovement

pip-vesselmovement-run-detached:
	$(Q) docker compose -f docker/docker-compose.yaml up --build vesselmovement -d

pip-vesselmovement-logs:
	$(Q) docker compose -f docker/docker-compose.yaml logs vesselmovement -f

pip-vesselmovement-down:
	$(Q) docker compose -f docker/docker-compose.yaml down vesselmovement
