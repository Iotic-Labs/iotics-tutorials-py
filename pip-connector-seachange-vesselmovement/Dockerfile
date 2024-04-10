ARG PYTHON_VERSION=3.10

# Builder Stage
FROM python:${PYTHON_VERSION}-slim-bullseye as builder

# Set the timezone environment variable to Europe/London
ENV TZ Europe/London

WORKDIR /app
COPY pip-connector-seachange-common /app/pip-connector-seachange-common
COPY pip-connector-seachange-vesselmovement /app/pip-connector-seachange-vesselmovement

RUN pip install --no-cache-dir build~=0.9.0 && \
    python3 -m build --wheel --outdir /app/dist/ pip-connector-seachange-common && \
    python3 -m build --wheel --outdir /app/dist/ pip-connector-seachange-vesselmovement

# Runtime Stage
FROM python:${PYTHON_VERSION}-slim-bullseye as runtime

# Create a non-root user
RUN useradd pip \
    && mkdir -p /home/pip \
    && chown -R pip:pip /home/pip

WORKDIR /home/pip/app

ENV PATH=${PATH}:/home/pip/.local/bin

# Copy from the builder stage
COPY --from=builder /app/dist/pip_connector_seachange*.whl \
    /app/pip-connector-seachange-vesselmovement/src/pip/connector/seachange/vesselmovement/* \
    /app/pip-connector-seachange-common/src/pip/connector/seachange/common/* \
    /home/pip/app/

# Change ownership
RUN chown -R pip:pip /home/pip
USER pip:pip

# Install application dependencies
RUN pip install --no-cache-dir build~=0.9.0 \
    && pip install --no-cache-dir --user --no-warn-script-location /home/pip/app/pip_connector_seachange*.whl \
    && rm /home/pip/app/*.whl
