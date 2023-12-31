# streamlink recorder docker

## 빠른 실행

```bash
# 트위치 다운로드
docker run --rm \
  --name twitch-hanryang1125 \
  -e TARGET_URL=https://www.twitch.tv/hanryang1125 \
  -e TARGET_STREAM=best \
  -e STREAMLINK_ARGS="--twitch-api-header=Authorization=OAuth abcdefghijklmnopqrstuvwxyz0123" \
  -e FFMPEG_SEGMENT_SIZE=690 \
  -e DISCORD_WEBHOOK=https://... \
  -e HTTP_PROXY=http://localhost:8888 \
  -e HTTPS_PROXY=http://localhost:8888 \
  --user 1000:1000 \
  -v ./data:/data \
  -v /etc/localtime:/etc/localtime:ro \
  streamlink-recorder
```

```bash
# 포크된 개발 빌드 버전 사용
docker run --rm \
  --name chzzk-funzinnu \
  -e STREAMLINK_GITHUB=https://github.com/fml09/streamlink \
  -e TARGET_URL=https://chzzk.naver.com/live/7d4157ae4fddab134243704cab847f23 \
  -e TARGET_STREAM=best \
  -e FFMPEG_SEGMENT_SIZE=690 \
  --user 1000:1000 \
  -v ./data:/data \
  -v /etc/localtime:/etc/localtime:ro \
  streamlink-recorder
```

## 환경 변수

- TARGET_URL

다운로드 할 주소. streamlink cli의 `URL`과 동일

- TARGET_STREAM

다운로드할 스트림(화질). streamlink cli의 `STREAM`과 동일

`기본값: best`

- STREAMLINK_GITHUB

이 값이 설정되면 streamlink를 해당 깃허브 주소로부터 설치함. 개발 중인 버전을 사용하고자 할 때 설정. 예시: `https://github.com/fml09/streamlink`

`기본값: None`

- STREAMLINK_COMMIT

이 값이 설정되면 공식 streamlink에서 해당 커밋 버전으로 패키지를 설치함. 예시: `refs/pull/PULL-REQUEST-ID/head`, `eb3decaf4d6a0081e71262e9ca0599e43aa26456`,

`기본값: None`

- STREAMLINK_VERSION

이 값이 설정되면 공식 streamlink 빌드 중에서 해당하는 버전을 설치함.

`기본값: None`

만약 위 변수 (`STREAMLINK_GITHUB`, `STREAMLINK_COMMIT`, `STREAMLINK_VERSION`)가 설정되지 않으면 가장 최신의 streamlink를 설치함.

- STREAMLINK_ARGS

streamlink cli에 그대로 전달되는 cli 인자. streamlink cli의 `OPTIONS`와 동일

- CHECK_INTERVAL

`TARGET_URL`이 방송 중인지 확인하는 간격.

`기본값: 15`

- FILEPATH_TEMPLATE

저장될 파일 경로와 파일 명의 템플릿. streamlink으로부터 얻은 값과 python datetime 모듈을 사용하여 템플릿을 완성함. `/`으로 시작할 수 없음.

`기본값: {plugin}/{author}/%Y-%m/[%Y%m%d_%H%M%S][{category}] {title} ({id})`

사용 가능한 키워드 목록:

> `plugin`, `id`, `author`, `category`, `title`, `stream`

- DISCORD_WEBHOOK

스트림(방송)의 시작과 종료 시에 메시지를 받을 디스코드 웹 훅 주소.

- FFMPEG_SEGMENT_SIZE

한 파일의 최대 길이. 단위: 분

예를 들어 60으로 설정하면 60분이 넘어가는 파일은 여러 개의 동영상으로 분할된다.
