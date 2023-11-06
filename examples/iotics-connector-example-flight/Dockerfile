ARG PYTHON_VERSION=3.10

# Builder Stage
FROM python:${PYTHON_VERSION}-slim-bullseye as builder

WORKDIR /app
COPY iotics-connector-example-grpc /app/iotics-connector-example-grpc
COPY iotics-connector-example-flight /app/iotics-connector-example-flight

RUN pip install --no-cache-dir build~=0.9.0 && \
    python3 -m build --wheel --outdir /app/dist/ iotics-connector-example-grpc && \
    python3 -m build --wheel --outdir /app/dist/ iotics-connector-example-flight

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
    /app/iotics-connector-example-flight/src/iotics/connector/example/flight/* \
    /app/iotics-connector-example-grpc/src/iotics/connector/example/grpc/* \
    /home/iotics/app/

# Change ownership
RUN chown -R iotics:iotics /home/iotics \
    && chown iotics:iotics /home/iotics/app/*.whl

USER iotics:iotics

# Install application dependencies
RUN pip install --no-cache-dir build~=0.9.0 \
    && pip install --no-cache-dir --user --no-warn-script-location /home/iotics/app/iotics_connector_example*.whl \
    && rm /home/iotics/app/*.whl
