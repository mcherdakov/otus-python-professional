FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE 1

RUN pip install pipenv
COPY app/Pipfile .
COPY app/Pipfile.lock .

RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy
ENV PATH="/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

COPY app/ app/
