FROM python:3.12-slim



USER root

RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y \
      git wget ffmpeg \
  && apt-get clean autoclean \
  && apt-get autoremove --yes \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -r -m -u 1000 -s /bin/bash abc \
  && usermod -aG sudo abc \
  &&  echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
  && mkdir -p /app \
  && chown -R abc:abc /app

COPY ./entrypoint.py /app/entrypoint.py
COPY ./util /app/util

RUN mkdir /data /plugins \
  && chown -R abc:abc /data \
  && chown -R abc:abc /plugins



USER abc

RUN pip install requests

ENV PATH="$HOME/.local/bin:$PATH"

WORKDIR /data 

VOLUME [ "/data", "/plugins", "/app" ]

ENTRYPOINT [ "python3", "/app/entrypoint.py" ]
