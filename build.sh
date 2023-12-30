#!/usr/bin/env bash 

set -ex

docker build \
  --tag streamlink-recorder:latest \
  .

