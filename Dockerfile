FROM python:3.12-slim



USER root

RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y \
      git wget sudo \
      curl ffmpeg \
  && apt-get clean autoclean \
  && apt-get autoremove --yes \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -r -m -u 1000 -s /bin/bash abc \
  && usermod -aG sudo abc \
  && mkdir -p /app \
  && chown -R abc:abc /app

RUN echo 'abc ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

COPY ./entrypoint.py /app/entrypoint.py
COPY ./util /app/util

RUN mkdir /data /plugins /log \
  && chown -R abc:abc /data \
  && chown -R abc:abc /plugins \
  && chown -R abc:abc /log



USER abc

RUN pip install --upgrade pip \
  && pip install requests

ENV PATH="$HOME/.local/bin:$PATH"

WORKDIR /data 

VOLUME [ "/data", "/plugins", "/app", "/log" ]

HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 CMD curl -f https://google.com || exit 1

ENTRYPOINT [ "python3", "/app/entrypoint.py" ]
