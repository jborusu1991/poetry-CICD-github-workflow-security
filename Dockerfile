ARG PYPI_INDEX_URL=https://nexus.dev.net/repository/ow-pypi/simple
ARG PYPI_TRUSTED_HOST=nexus.dev.net
ARG PYTHON_VERSION=3.12
ARG FUNCTION_DIR="/function"

FROM python:$PYTHON_VERSION AS build
ARG PYPI_INDEX_URL
ARG PYPI_TRUSTED_HOST
ARG PYTHON_VERSION

RUN pip install poetry \
    --no-cache-dir \
    --index-url $PYPI_INDEX_URL \
    --trusted-host $PYPI_TRUSTED_HOST

COPY ./src/ /app/src/
COPY ./pyproject.toml /app/
COPY ./poetry.lock /app/
COPY ./README.md /app/

WORKDIR /app

RUN poetry build

FROM python:$PYTHON_VERSION
ARG PYPI_INDEX_URL
ARG PYPI_TRUSTED_HOST
ARG PYTHON_VERSION
ARG FUNCTION_DIR

LABEL maintainer="jborusu@ow.net"

WORKDIR ${FUNCTION_DIR}

ENV AMQ_CONNECTION  10.186.45.12:61613,10.186.45.16:61613
ENV AMQ_QUEUE_PREFIX net.ow
ENV LOG_LEVEL INFO


COPY --from=build /app/dist/*.whl ./

RUN pip install ./*.whl \
    --no-cache-dir \
    --index-url $PYPI_INDEX_URL \
    --trusted-host $PYPI_TRUSTED_HOST

# lambda handler (add handler function to main.py)
ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["mylambda-app.lambda.handler"]

