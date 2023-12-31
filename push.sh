#!/usr/bin/env bash

set -ex

docker image tag streamlink-recorder:latest k123s456h/streamlink-recorder:latest

docker push k123s456h/streamlink-recorder:latest
