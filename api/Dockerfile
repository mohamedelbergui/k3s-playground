FROM python:3.12-slim

WORKDIR /api
COPY requirements.txt .
COPY pip_cache/ /pip_cach/

RUN ["pip","install","--no-index", "--find-links=/pip_cach","-r","requirements.txt"]

COPY . .

CMD [ "python", "app.py" ]