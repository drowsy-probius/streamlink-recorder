import os 
import sys
import time
import subprocess
import threading
import traceback
import json
from datetime import datetime

from util.common import send_discord_message
from util.stream_metadata import StreamMetadata
from util.stream import run_command_and_get_stdout, install_streamlink, format_filepath, truncate_string_in_byte_size


STREAMLINK_GITHUB = os.getenv('STREAMLINK_GITHUB', None)
STREAMLINK_COMMIT = os.getenv('STREAMLINK_COMMIT', None)
STREAMLINK_VERSION = os.getenv('STREAMLINK_VERSION', None)
TARGET_URL = os.getenv('TARGET_URL', None)
TARGET_STREAM = os.getenv('TARGET_STREAM', 'best')
STREAMLINK_ARGS = os.getenv('STREAMLINK_ARGS', None)

CHECK_INTERVAL = float(os.getenv('CHECK_INTERVAL', 10))
FILEPATH_TEMPLATE = os.getenv('FILEPATH_TEMPLATE', "{plugin}/{author}/%Y-%m/[%Y%m%d_%H%M%S][{category}] {title} ({id})")
FFMPEG_SEGMENT_SIZE = int(os.getenv('FFMPEG_SEGMENT_SIZE', None))

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', None)

def handle_process_stdout(process: subprocess.Popen):
    while process.returncode is None:
        for line in process.stdout.readline():
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            sys.stdout.write(str(line))
        sys.stdout.flush()


def handle_process_stderr(process: subprocess.Popen):
    while process.returncode is None:
        for line in process.stderr.readline():
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            sys.stdout.write(str(line))
        sys.stdout.flush()

def check_and_download(target_url: str, target_stream: str, streamlink_args: str):
    try:
        metadata_store = StreamMetadata(target_url)
        
        if not metadata_store.is_online:
            return

        print(f'[{datetime.now().strftime("%Y%m%d_%H%M%S")}] start download', flush=True)

        current_metadata = metadata_store.get_latest_metadata()

        plugin = current_metadata['plugin']
        metadata_id = current_metadata['id']
        metadata_author = current_metadata['author']
        metadata_category = current_metadata['category']
        metadata_title = current_metadata['title']
        metadata_datetime = current_metadata['datetime']
        
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
            filepath += ' part%02d'
        
        filepath_with_extname = filepath + '.ts'
        ffmpeg_command += [filepath_with_extname]

        print(streamlink_command, flush=True)
        print(ffmpeg_command, flush=True)

        streamlink_process = subprocess.Popen(
            streamlink_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
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
    except Exception as e:
        send_discord_message(f"[ERROR][{plugin}][{metadata_author}][{metadata_category}] {metadata_title} ({metadata_id})\n{traceback.format_exc()}", discord_webhook=DISCORD_WEBHOOK)
        traceback.print_exc()
    finally:
        send_discord_message(f"[OFF][{plugin}][{metadata_author}][{metadata_category}] {metadata_title} ({metadata_id})", discord_webhook=DISCORD_WEBHOOK)



print(install_streamlink(STREAMLINK_GITHUB, STREAMLINK_COMMIT, STREAMLINK_VERSION), flush=True)
print(run_command_and_get_stdout(f'''{sys.executable} -m streamlink --version'''), flush=True)
print(run_command_and_get_stdout('ffmpeg -version'), flush=True)

run_command_and_get_stdout("ln -s ~/.local/share/streamlink/plugins /plugins")

while True:
    check_and_download(TARGET_URL, TARGET_STREAM, STREAMLINK_ARGS)
    print(f'[{datetime.now().strftime("%Y%m%d_%H%M%S")}] sleep', flush=True)
    time.sleep(CHECK_INTERVAL)