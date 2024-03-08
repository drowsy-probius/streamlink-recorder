import os
import sys
import time
import math
import subprocess
import traceback
import json
import signal
import threading
import gc
from typing import Dict, List
from copy import deepcopy

from util.logger import main_logger, subprocess_logger
from util.common import (
    send_discord_message,
    truncate_string_in_byte_size,
    format_filepath,
    get_stdout_of_command,
    get_output_of_command,
    silent_of,
)
from util.event import Subscriber
from util.stream_metadata import StreamMetadata
from util.stream import install_streamlink


STREAMLINK_GITHUB = os.getenv("STREAMLINK_GITHUB", None)
STREAMLINK_COMMIT = os.getenv("STREAMLINK_COMMIT", None)
STREAMLINK_VERSION = os.getenv("STREAMLINK_VERSION", None)
TARGET_URL = os.getenv("TARGET_URL", None)
TARGET_STREAM = os.getenv("TARGET_STREAM") or "best"
STREAMLINK_ARGS = os.getenv("STREAMLINK_ARGS", "")

CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL") or 15)
FILEPATH_TEMPLATE = os.getenv("FILEPATH_TEMPLATE", "{plugin}/{author}/%Y-%m/[%Y%m%d_%H%M%S][{category}] {title} ({id})")
FFMPEG_SEGMENT_SIZE = int(os.getenv("FFMPEG_SEGMENT_SIZE") or 690)

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", None)

# preserve max 10 stream ids per each clf
SENT_MESSAGE_STREAM_IDS: Dict[str, List[str]] = {}


class RecordException(Exception):
    pass


@silent_of
def send_discord_message_if_necessary(clf: str, stream_id: str, message: str):
    if clf not in SENT_MESSAGE_STREAM_IDS:
        SENT_MESSAGE_STREAM_IDS[clf] = []
    elif stream_id in SENT_MESSAGE_STREAM_IDS[clf]:
        return
    SENT_MESSAGE_STREAM_IDS[clf] = SENT_MESSAGE_STREAM_IDS[clf][-9:] + [stream_id]
    main_logger.debug("%s sent_stream_ids: %s", clf, SENT_MESSAGE_STREAM_IDS[clf])
    send_discord_message(f"[{clf}]{message}", discord_webhook=DISCORD_WEBHOOK)


def handle_process_stdout(process: subprocess.Popen):
    subprocess_logger.debug("run")
    while process.returncode is None:
        gc.collect()
        line = process.stdout.readline()
        process.stdout.flush()
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        subprocess_logger.info(str(line).rstrip())
        process.poll()
    subprocess_logger.debug("done")


def handle_process_stderr(process: subprocess.Popen):
    subprocess_logger.debug("run")
    while process.returncode is None:
        gc.collect()
        line = process.stderr.readline()
        process.stderr.flush()
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        subprocess_logger.info(str(line).rstrip())
        process.poll()
    subprocess_logger.debug("done")


def export_metadata_thread(filepath: str, store: StreamMetadata):
    stream_info_subscriber = Subscriber("stream_info")
    try:
        [target_dirpath, _] = os.path.split(filepath)
        os.makedirs(target_dirpath, exist_ok=True)
        os.system(f'''sudo chown -R abc:abc "{target_dirpath}"''')

        main_logger.info("write metadata to file")
        metadata_stack = deepcopy(store.last_stack)
        with open(f"{filepath}.json", "w", encoding="utf8") as f:
            json.dump(metadata_stack, f, ensure_ascii=False, indent=2)
    except Exception as e:
        main_logger.error(e)
        main_logger.error(traceback.print_exc())

    store.add_subscriber(stream_info_subscriber, "stream_info")
    while store.is_online:
        gc.collect()
        result = stream_info_subscriber.receive(0.5)
        if result is None:
            continue

        try:
            main_logger.info("update metadata to file")
            metadata_stack = deepcopy(store.stack)
            with open(f"{filepath}.json", "w", encoding="utf8") as f:
                json.dump(metadata_stack, f, ensure_ascii=False, indent=2)
            stream_info_subscriber.event.clear()
        except Exception as e:
            main_logger.error(e)
            main_logger.error(traceback.print_exc())
    store.remove_subscriber(stream_info_subscriber, "stream_info")


def sleep_if_1080_not_available(metadata_store: StreamMetadata, target_stream: str, check_interval: float) -> bool:
    target_streams = target_stream.split(",")
    is_1080_in_target = len([target for target in target_streams if "1080" in target]) > 0

    nth_try = 0
    while nth_try <= 2:
        gc.collect()
        stream_types = metadata_store.get_stream_types()
        is_1080_in_stream = stream_types and len([stream for stream in stream_types if "1080" in stream]) > 0

        if not is_1080_in_target or is_1080_in_stream:
            return

        main_logger.info("1080 is not in stream. It may be target site error. So wait for some seconds.")
        time.sleep(check_interval)
        nth_try += 1


def download_stream(metadata_store: StreamMetadata, target_url: str, target_stream: str, streamlink_args: str):
    streamlink_process = None
    ffmpeg_process = None
    filepath = None

    def interrupt_handler(__signalnum, __frame):
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, signal.default_int_handler)
        signal.signal(signal.SIGABRT, signal.default_int_handler)
        if ffmpeg_process:
            ffmpeg_process.poll()
            if ffmpeg_process.returncode is None:
                ffmpeg_process.kill()
        if streamlink_process:
            streamlink_process.poll()
            if streamlink_process.returncode is None:
                streamlink_process.kill()
        signal.raise_signal(__signalnum)

    signal.signal(signal.SIGINT, interrupt_handler)
    signal.signal(signal.SIGTERM, interrupt_handler)
    signal.signal(signal.SIGABRT, interrupt_handler)

    try:
        current_metadata = metadata_store.get_current_metadata()
        if not current_metadata:
            return

        plugin = current_metadata["plugin"]
        metadata_id = current_metadata["id"]
        metadata_author = current_metadata["author"]
        metadata_category = current_metadata["category"]
        metadata_title = current_metadata["title"]
        metadata_datetime = current_metadata["datetime"]

        main_logger.info("download starts")
        main_logger.info(current_metadata)
        discord_message_template = (
            f"[{plugin}][{metadata_author}][{metadata_category}] {metadata_title} ({metadata_id})"
        )
        send_discord_message_if_necessary("ON", metadata_id, discord_message_template)

        filepath = os.path.join(
            "/data",
            format_filepath(
                FILEPATH_TEMPLATE,
                plugin=plugin,
                metadata_id=metadata_id,
                metadata_author=metadata_author,
                metadata_category=metadata_category,
                metadata_title=metadata_title,
            ),
        )

        [dirpath, filename] = os.path.split(filepath)
        os.makedirs(dirpath, exist_ok=True)
        os.system(f'''sudo chown -R abc:abc "{dirpath}"''')

        streamlink_command = [
            sys.executable,
            "-m",
            "streamlink",
            "-O",
        ]
        streamlink_command += [target_url, target_stream]
        if streamlink_args:
            streamlink_command += [streamlink_args]

        ffmpeg_command = [
            "ffmpeg",
            "-i",
            "-",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "-metadata",
            f"title={truncate_string_in_byte_size(metadata_title, 147)}",
            "-metadata",
            f"artist={metadata_author}",
            "-metadata",
            f"genre={metadata_category}",
            "-metadata",
            f"date={metadata_datetime}",
        ]

        filepath: str = os.path.join(dirpath, filename)
        # ffmpeg templace escape percent character
        ffmpeg_filepath = filepath.replace("%", "%%")

        filepath_with_extname = ffmpeg_filepath
        if FFMPEG_SEGMENT_SIZE is not None:
            ffmpeg_command += [
                "-f",
                "segment",
                "-segment_time",
                str(FFMPEG_SEGMENT_SIZE * 60),
                "-reset_timestamps",
                "1",
                "-segment_start_number",
                "1",
            ]
            filepath_with_extname += " part%d"

        filepath_with_extname += ".ts"
        ffmpeg_command += [filepath_with_extname]

        streamlink_process = subprocess.Popen(
            streamlink_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        ffmpeg_process = subprocess.Popen(
            ffmpeg_command,
            stdin=streamlink_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore",
        )

        if metadata_store.is_online:
            main_logger.info(streamlink_command)
            main_logger.info(ffmpeg_command)

        time.sleep(2)
        if streamlink_process.poll() is None and ffmpeg_process.poll() is None:
            metadata_export_thread = threading.Thread(target=export_metadata_thread, args=(filepath, metadata_store))
            metadata_export_thread.daemon = True
            metadata_export_thread.start()

        streamlink_log_thread = threading.Thread(target=handle_process_stderr, args=(streamlink_process,))
        streamlink_log_thread.daemon = True
        streamlink_log_thread.start()
        if streamlink_log_thread is None:
            raise RecordException("Cannot spawn streamlink log thread")

        ffmpeg_log_thread = threading.Thread(target=handle_process_stdout, args=(ffmpeg_process,))
        ffmpeg_log_thread.start()
        if ffmpeg_log_thread is None:
            raise RecordException("Cannot spawn ffmpeg log thread")
        ffmpeg_log_thread.join()

        streamlink_returncode = streamlink_process.wait()
        if streamlink_returncode != 0:
            if streamlink_process.stderr and not streamlink_process.stderr.closed:
                streamlink_stderr = streamlink_process.stderr.readlines()
                streamlink_stderr = [str(output) for output in streamlink_stderr]
            main_logger.warning(
                "streamlink not exited normally.\nreturncode: %s.\nstdout: %s",
                streamlink_returncode,
                streamlink_stderr,
            )

        ffmpeg_returncode = ffmpeg_process.wait()
        if ffmpeg_returncode != 0:
            if ffmpeg_process.stdout and not ffmpeg_process.stdout.closed:
                ffmpeg_stdout = ffmpeg_process.stdout.readlines()
                ffmpeg_stdout = [str(output) for output in ffmpeg_stdout]
            main_logger.warning(
                "ffmpeg not exited normally.\nreturncode: %s.\nstdout: %s",
                ffmpeg_returncode,
                ffmpeg_stdout,
            )

        ffmpeg_process.terminate()
        streamlink_process.terminate()

        # force update status
        metadata_store.set_metadata()

        main_logger.info("download ends")
        send_discord_message_if_necessary("OFF", metadata_id, discord_message_template)
    except Exception as e:
        send_discord_message(f"[ERROR]{discord_message_template}", discord_webhook=DISCORD_WEBHOOK)
        raise e
    finally:
        if ffmpeg_process:
            ffmpeg_process.poll()
            if ffmpeg_process.returncode is None:
                ffmpeg_process.kill()
        if streamlink_process:
            streamlink_process.poll()
            if streamlink_process.returncode is None:
                streamlink_process.kill()


main_logger.info(install_streamlink(STREAMLINK_GITHUB, STREAMLINK_COMMIT, STREAMLINK_VERSION))
main_logger.info(get_stdout_of_command([sys.executable, "-m", "streamlink", "--version"]))
main_logger.info(get_stdout_of_command(["ffmpeg", "-version"]))

get_output_of_command(["ln", "-s", "/plugins", "~/.local/share/streamlink/plugins"])


def download_pipeline():
    metadata_store = StreamMetadata(TARGET_URL, STREAMLINK_ARGS, CHECK_INTERVAL)
    sleep_if_1080_not_available(metadata_store, TARGET_STREAM, CHECK_INTERVAL)
    # when stream is stable, check several times
    for _ in range(math.ceil(CHECK_INTERVAL / 3)):
        download_stream(metadata_store, TARGET_URL, TARGET_STREAM, STREAMLINK_ARGS)
        time.sleep(1)


def main_loop():
    while True:
        gc.collect()

        try:
            download_pipeline()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            main_logger.error(e)
            main_logger.error(traceback.format_exc())


if __name__ == "__main__":
    main_loop()
