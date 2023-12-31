import os 
import sys
import time
import subprocess
import threading
import traceback
import json
from copy import deepcopy

from util.logger import main_logger, subprocess_logger
from util.common import (
    run_command_and_get_stdout, 
    replace_unavailable_characters_in_filename, 
    send_discord_message, 
    truncate_string_in_byte_size, 
    format_filepath
)
from util.stream_metadata import StreamMetadata
from util.stream import install_streamlink


STREAMLINK_GITHUB = os.getenv('STREAMLINK_GITHUB', None)
STREAMLINK_COMMIT = os.getenv('STREAMLINK_COMMIT', None)
STREAMLINK_VERSION = os.getenv('STREAMLINK_VERSION', None)
TARGET_URL = os.getenv('TARGET_URL', None)
TARGET_STREAM = os.getenv('TARGET_STREAM', 'best')
STREAMLINK_ARGS = os.getenv('STREAMLINK_ARGS', None)

CHECK_INTERVAL = float(os.getenv('CHECK_INTERVAL', 15))
FILEPATH_TEMPLATE = os.getenv('FILEPATH_TEMPLATE', "{plugin}/{author}/%Y-%m/[%Y%m%d_%H%M%S][{category}] {title} ({id})")
FFMPEG_SEGMENT_SIZE = int(os.getenv('FFMPEG_SEGMENT_SIZE', None))

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', None)

def handle_process_stdout(process: subprocess.Popen):
    subprocess_logger.debug('run')
    while process.returncode is None:
        line = process.stdout.readline()
        process.stdout.flush()
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='ignore')
        subprocess_logger.info(str(line).rstrip())
        process.poll()
    subprocess_logger.debug('done')

def handle_process_stderr(process: subprocess.Popen):
    subprocess_logger.debug('run')
    while process.returncode is None:
        line = process.stderr.readline()
        process.stderr.flush()
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='ignore')
        subprocess_logger.info(str(line).rstrip())
        process.poll()
    subprocess_logger.debug('done')

def sleep_if_1080_not_available(metadata_store: StreamMetadata, target_stream: str, check_interval: float) -> bool:    
    target_streams = target_stream.split(',')
    is_1080_in_target = len(
        [target for target in target_streams if '1080' in target]
    ) > 0

    nth_try = 0
    while nth_try <= 2:
        stream_types = metadata_store.get_stream_types()
        is_1080_in_stream = stream_types and len(
            [stream for stream in stream_types if '1080' in stream]
        ) > 0
        
        if is_1080_in_target == False or is_1080_in_stream == True:
            return

        main_logger.info('1080 is not in stream. It may be target site error. So wait for some seconds.')
        time.sleep(check_interval)
        nth_try += 1

def download_stream(metadata_store: StreamMetadata, target_url: str, target_stream: str, streamlink_args: str):
    try:
        current_metadata = metadata_store.get_latest_metadata()

        plugin = current_metadata['plugin']
        metadata_id = current_metadata['id']
        metadata_author = current_metadata['author']
        metadata_category = current_metadata['category']
        metadata_title = current_metadata['title']
        metadata_datetime = current_metadata['datetime']
        
        main_logger.info("download starts")
        main_logger.info(current_metadata)
        send_discord_message(f"[ON][{plugin}][{metadata_author}][{metadata_category}] {metadata_title} ({metadata_id})", discord_webhook=DISCORD_WEBHOOK)
    
        filepath = os.path.join(
            '/data', 
            format_filepath(
                FILEPATH_TEMPLATE, 
                plugin=plugin,
                metadata_id=metadata_id,
                metadata_author=metadata_author,
                metadata_category=metadata_category,
                metadata_title=metadata_title
                )
            )
        filepath = '/'.join([
            replace_unavailable_characters_in_filename(linkname)
            for linkname in filepath.split('/')
        ])
        [*dirpath, filename] = filepath.split('/')
        os.makedirs('/'.join(dirpath), exist_ok=True)
        os.system(f'sudo chown -R abc:abc "{dirpath}"')
        
        streamlink_command = [
            sys.executable, '-m', 
            'streamlink', 
            '--retry-max', '3',
            '-O',
        ]
        if streamlink_args:
            streamlink_command += [streamlink_args]
        streamlink_command += [
            target_url, 
            target_stream
        ]
        
        
        ffmpeg_command = [
            'ffmpeg',
            '-i', '-',
            '-c', 'copy',
            '-movflags', '+faststart',
            '-metadata', f'title={truncate_string_in_byte_size(metadata_title, 147)}',
            '-metadata', f'artist={metadata_author}',
            '-metadata', f'genre={metadata_category}',
            '-metadata', f'date={metadata_datetime}',
        ]
        
        filepath: str = '/'.join([*dirpath, filename])
        # ffmpeg templace escape percent character
        filepath = filepath.replace('%', '%%')
        
        filepath_with_extname = filepath
        if FFMPEG_SEGMENT_SIZE is not None:
            ffmpeg_command += [
                '-f', 'segment', 
                '-segment_time', str(FFMPEG_SEGMENT_SIZE*60), 
                '-reset_timestamps', '1', 
                '-segment_start_number', '1'
            ]
            filepath_with_extname += ' part%d'
        
        filepath_with_extname += '.ts'
        ffmpeg_command += [filepath_with_extname]

        main_logger.info(streamlink_command)
        main_logger.info(ffmpeg_command)

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

        streamlink_log_thread = threading.Thread(target=handle_process_stderr, args=(streamlink_process,))
        streamlink_log_thread.daemon = True
        streamlink_log_thread.start()
        if streamlink_log_thread is None:
            raise Exception('Cannot spawn streamlink log thread')

        ffmpeg_log_thread = threading.Thread(target=handle_process_stdout, args=(ffmpeg_process,))
        ffmpeg_log_thread.start()
        if ffmpeg_log_thread is None:
            raise Exception('Cannot spawn ffmpeg log thread')
        ffmpeg_log_thread.join()
        
        ffmpeg_returncode = ffmpeg_process.wait() 
        if ffmpeg_returncode != 0:
            raise Exception(f'ffmpeg not exited normally. returncode: {ffmpeg_returncode}')

        metadata_stack = deepcopy(metadata_store.stack)

        ffmpeg_process.terminate()
        streamlink_process.terminate()

        with open(f'{filepath}.json', 'w', encoding='utf8') as f:
            json.dump(metadata_stack, f, ensure_ascii=False, indent=2)

        main_logger.info("download ends")
        send_discord_message(f"[OFF][{plugin}][{metadata_author}][{metadata_category}] {metadata_title} ({metadata_id})", discord_webhook=DISCORD_WEBHOOK)
    except Exception as e:
        send_discord_message(f"[ERROR][{plugin}][{metadata_author}][{metadata_category}] {metadata_title} ({metadata_id})\n{traceback.format_exc()}", discord_webhook=DISCORD_WEBHOOK)
        raise e




main_logger.info(
    install_streamlink(STREAMLINK_GITHUB, STREAMLINK_COMMIT, STREAMLINK_VERSION)
)
main_logger.info(
    run_command_and_get_stdout(f'''{sys.executable} -m streamlink --version''')
)
main_logger.info(
    run_command_and_get_stdout('ffmpeg -version')
)

run_command_and_get_stdout("ln -s ~/.local/share/streamlink/plugins /plugins")

metadata_store = StreamMetadata(TARGET_URL, CHECK_INTERVAL)

while True:
    if not metadata_store.is_online:
        time.sleep(0.5)
        continue

    try:
        sleep_if_1080_not_available(metadata_store, TARGET_STREAM, CHECK_INTERVAL)
        download_stream(metadata_store, TARGET_URL, TARGET_STREAM, STREAMLINK_ARGS)
    except Exception as e:
        main_logger.error(traceback.format_exc())

