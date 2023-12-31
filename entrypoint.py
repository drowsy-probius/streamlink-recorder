import os 
import sys
import time
import subprocess
import threading
import traceback
import json
from typing import Optional

from util.logger import main_logger, subprocess_logger
from util.common import send_discord_message, truncate_string_in_byte_size, format_filepath
from util.stream_metadata import StreamMetadata
from util.stream import run_command_and_get_stdout, install_streamlink


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
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='ignore')
        subprocess_logger.info(str(line).rstrip())
        process.poll()
    subprocess_logger.debug('done')

def handle_process_stderr(process: subprocess.Popen):
    subprocess_logger.debug('run')
    while process.returncode is None:
        line = process.stderr.readline()
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='ignore')
        subprocess_logger.info(str(line).rstrip())
        process.poll()
    subprocess_logger.debug('done')

def check_stream(target_url: str, target_stream: str, check_interval: float, nth_try=0) -> Optional[StreamMetadata]:
    metadata_store = StreamMetadata(target_url, check_interval)
    
    if not metadata_store.is_online:
        metadata_store.destroy()
        return

    target_streams = target_stream.split(',')
    stream_types = metadata_store.get_stream_types()
    is_1080_in_target = len(
        [target for target in target_streams if '1080' in target]
    ) > 0
    is_1080_in_stream = stream_types and len(
        [stream for stream in stream_types if '1080' in stream]
    ) > 0
    
    if is_1080_in_target == True and is_1080_in_stream == False:
        if nth_try > 2:
            metadata_store.destroy()
            return

        main_logger.info('1080 is not in stream. It may be target site error. So wait for some seconds.')
        time.sleep(check_interval)
        return check_stream(target_url, target_stream, check_interval, nth_try=(nth_try+1))
    
    return metadata_store


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
        [*dirpath, filename] = filepath.split('/')
        os.makedirs('/'.join(dirpath), exist_ok=True)
        
        streamlink_command = [sys.executable, '-m', 'streamlink', '-O', target_url, target_stream]
        if streamlink_args:
            streamlink_command += [streamlink_args]
        
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
        
        if FFMPEG_SEGMENT_SIZE is not None:
            ffmpeg_command += [
                '-f', 'segment', 
                '-segment_time', str(FFMPEG_SEGMENT_SIZE*60), 
                '-reset_timestamps', '1', 
                '-segment_start_number', '1'
            ]
            filepath += ' part%d'
        
        filepath_with_extname = filepath + '.ts'
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

        ffmpeg_process.terminate()
        streamlink_process.terminate()

        with open(f'{filepath}.json', 'w', encoding='utf8') as f:
            json.dump(metadata_store.stack, f, ensure_ascii=False, indent=2)

        metadata_store.destroy()
        
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

while True:
    try:
        metadata_store = check_stream(TARGET_URL, TARGET_STREAM, CHECK_INTERVAL)
        if metadata_store:
            download_stream(metadata_store, TARGET_URL, TARGET_STREAM, STREAMLINK_ARGS)
    except Exception as e:
        main_logger.error(traceback.format_exc())
    main_logger.debug("sleep")
    time.sleep(CHECK_INTERVAL)
