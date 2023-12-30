#!/usr/bin/env bash 

set -ex

docker buildx build \
  --push \
  --platform linux/amd64 \
  --tag k123s456h/streamlink-recorder:latest \
  .
