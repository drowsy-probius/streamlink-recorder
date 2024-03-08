#!/usr/bin/env bash 

set -ex

docker run -it --rm \
  --name streamlink-recorder \
  -e TARGET_URL=https://www.twitch.tv/nishimura_honoka \
  -v ./output/data:/data \
  -v ./output/log:/log \
  --user 1000:1000 \
  streamlink-recorder:latest
