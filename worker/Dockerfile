FROM python:3.12-slim

WORKDIR /worker
COPY requirements.txt .
COPY pip_cache/ /pip_cach/

RUN ["pip","install","-r","requirements.txt"]

COPY . .

CMD [ "python", "worker.py" ]