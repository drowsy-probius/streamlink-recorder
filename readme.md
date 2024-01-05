# streamlink recorder docker

[한국어](./readme.ko.md)

## Quick Start

```bash
docker run --rm \
  --name twitch-hanryang1125 \
  -e TARGET_URL=https://www.twitch.tv/hanryang1125 \
  -e TARGET_STREAM=best \
  -e STREAMLINK_ARGS=--twitch-api-header=Authorization=OAuth abcdefghijklmnopqrstuvwxyz0123 \
  -e FFMPEG_SEGMENT_SIZE=690 \
  -e DISCORD_WEBHOOK=https://... \
  -e HTTP_PROXY=http://localhost:8888 \
  -e HTTPS_PROXY=http://localhost:8888 \
  --user 1000:1000 \
  -v ./data:/data \
  -v ./log/twitch-hanryang1125:/log \
  -v /etc/localtime:/etc/localtime:ro \
  streamlink-recorder
```

```bash
# use development stage build
docker run --rm \
  --name chzzk-funzinnu \
  -e STREAMLINK_GITHUB=https://github.com/fml09/streamlink \
  -e TARGET_URL=https://chzzk.naver.com/live/7d4157ae4fddab134243704cab847f23 \
  -e TARGET_STREAM=best \
  -e FFMPEG_SEGMENT_SIZE=690 \
  --user 1000:1000 \
  -v ./data:/data \
  -v ./log/chzzk-funzinnu:/log \
  -v /etc/localtime:/etc/localtime:ro \
  streamlink-recorder
```

## environment variables

- TARGET_URL

A URL to attempt to download streams from. Same as the argument `URL` of streamlink cli.

- TARGET_STREAM

A stream to download. Same as the argument `STREAM` of streamlink cli.

`default: best`

- STREAMLINK_GITHUB

If set the container installs streamlink from the given github repository. For example: `https://github.com/fml09/streamlink`

`default: None`

- STREAMLINK_COMMIT

If set the container installs given commit version from streamlink github. For example: `refs/pull/PULL-REQUEST-ID/head`, `eb3decaf4d6a0081e71262e9ca0599e43aa26456`,

`default: None`

- STREAMLINK_VERSION

If set the container installs given streamlink version from pip repository.

`default: None`

If all variables (`STREAMLINK_GITHUB`, `STREAMLINK_COMMIT`, `STREAMLINK_VERSION`) are not given, then the container installs the latest streamlink version.

- STREAMLINK_ARGS

This values are passed to streamlink. Same as the argument `OPTIONS` of streamlink cli.

Do not quote this value.

`default: ''`

- CHECK_INTERVAL

If set the container sleeps for given time in seconds when stream is not available.

`default: 15`

- FILEPATH_TEMPLATE

The container saves received stream to target filepath. It uses steamlink's keywords and python datetime keywords.

It should not starts with `/`.

`default: {plugin}/{author}/%Y-%m/[%Y%m%d_%H%M%S][{category}] {title} ({id})`

supported keywords:

> `plugin`, `id`, `author`, `category`, `title`, `stream`

- DISCORD_WEBHOOK

If set the container sends stream on and off message to discord.

- FFMPEG_SEGMENT_SIZE

If set the downloaded file splits. unit: min
