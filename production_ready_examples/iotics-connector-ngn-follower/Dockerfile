ARG PYTHON_VERSION=3.10

# Builder Stage
FROM python:${PYTHON_VERSION}-slim-bullseye as builder

WORKDIR /app
COPY iotics-connector-example-common /app/iotics-connector-example-common
COPY iotics-connector-ngn-follower /app/iotics-connector-ngn-follower

RUN pip install --no-cache-dir build~=0.9.0 && \
    python3 -m build --wheel --outdir /app/dist/ iotics-connector-example-common && \
    python3 -m build --wheel --outdir /app/dist/ iotics-connector-ngn-follower

# Runtime Stage
FROM python:${PYTHON_VERSION}-slim-bullseye as runtime

# Create a non-root user
RUN useradd iotics \
    && mkdir -p /home/iotics \
    && chown -R iotics:iotics /home/iotics

WORKDIR /home/iotics/app

ENV PATH=${PATH}:/home/iotics/.local/bin

# Copy from the builder stage
COPY --from=builder /app/dist/iotics_connector_ngn*.whl \
    /app/iotics-connector-ngn-follower/src/iotics/connector/ngn/follower/*.py \
    /app/iotics-connector-example-common/src/iotics/connector/example/common/* \
    /home/iotics/app/

# Copy templates folder and its contents
COPY --from=builder /app/iotics-connector-ngn-follower/src/iotics/connector/ngn/follower/templates \
    /home/iotics/app/templates

# Copy sensors folder and its contents
COPY --from=builder /app/iotics-connector-ngn-follower/src/iotics/connector/ngn/follower/sensors \
    /home/iotics/app/sensors

# Change ownership
RUN chown -R iotics:iotics /home/iotics
USER iotics:iotics

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Install application dependencies
RUN pip install --no-cache-dir build~=0.9.0 \
    && pip install --no-cache-dir --user --no-warn-script-location /home/iotics/app/iotics_connector_ngn*.whl \
    && rm /home/iotics/app/*.whl