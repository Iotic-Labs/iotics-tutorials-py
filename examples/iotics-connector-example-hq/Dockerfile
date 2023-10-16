ARG PYTHON_VERSION=3.10

FROM python:${PYTHON_VERSION}-slim-bullseye as builder

WORKDIR /work
COPY iotics-connector-example-common /work/iotics-connector-example-common
COPY iotics-connector-example-hq /work/iotics-connector-example-hq

RUN python3 -m pip install --no-cache-dir build~=0.9.0 && \
    python3 -m build --wheel --outdir /work/dist/ iotics-connector-example-common && \
    python3 -m build --wheel --outdir /work/dist/ iotics-connector-example-hq

FROM python:${PYTHON_VERSION}-slim-bullseye as runtime

RUN useradd iotics
RUN mkdir -p /home/iotics && chown -R iotics:iotics /home/iotics
WORKDIR /home/iotics/app

ENV PATH=${PATH}:/home/iotics/.local/bin

COPY --from=builder /work/dist/iotics_connector_example*.whl /home/iotics/app
COPY --from=builder /work/iotics-connector-example-hq/src/iotics/connector/example/hq/main.py /home/iotics/app
COPY --from=builder /work/iotics-connector-example-common/src/iotics/connector/example/common/* /home/iotics/app
RUN chown -R iotics:iotics /home/iotics

USER iotics:iotics

RUN python3 -m pip install \
    --user \
    --no-cache-dir \
    --no-warn-script-location \
    /home/iotics/app/iotics_connector_example*.whl && \
    rm /home/iotics/app/*.whl
