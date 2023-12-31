#!/usr/bin/env bash 

set -ex

docker buildx build \
  --platform linux/amd64 \
  --tag streamlink-recorder:latest \
  .
