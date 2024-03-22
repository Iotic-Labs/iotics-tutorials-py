ARG PYTHON_VERSION=3.10

# Builder Stage
FROM python:${PYTHON_VERSION}-slim-bullseye as builder

WORKDIR /app
COPY iotics-connector-example-common /app/iotics-connector-example-common
COPY iotics-connector-example-publisher /app/iotics-connector-example-publisher

RUN pip install --no-cache-dir build~=0.9.0 && \
    python3 -m build --wheel --outdir /app/dist/ iotics-connector-example-common && \
    python3 -m build --wheel --outdir /app/dist/ iotics-connector-example-publisher

# Runtime Stage
FROM python:${PYTHON_VERSION}-slim-bullseye as runtime

# Create a non-root user
RUN useradd iotics \
    && mkdir -p /home/iotics \
    && chown -R iotics:iotics /home/iotics

WORKDIR /home/iotics/app

ENV PATH=${PATH}:/home/iotics/.local/bin

# Copy from the builder stage
COPY --from=builder /app/dist/iotics_connector_example*.whl \
    /app/iotics-connector-example-publisher/src/iotics/connector/example/publisher/* \
    /app/iotics-connector-example-common/src/iotics/connector/example/common/* \
    /home/iotics/app/

# Change ownership
RUN chown -R iotics:iotics /home/iotics
USER iotics:iotics

# Install application dependencies
RUN pip install --no-cache-dir build~=0.9.0 \
    && pip install --no-cache-dir --user --no-warn-script-location /home/iotics/app/iotics_connector_example*.whl \
    && rm /home/iotics/app/*.whl
