FROM python:3-slim as requirements

RUN pip install poetry
COPY pyproject.toml poetry.lock /app/
WORKDIR /app
RUN poetry export > requirements.txt
RUN poetry export --dev > requirements.dev.txt

FROM python:3-slim as prod
COPY --from=requirements /app /app
WORKDIR /app
RUN pip install -r requirements.txt
COPY . /app

FROM prod as dev
RUN pip install -r requirements.dev.txt
