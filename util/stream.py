import subprocess
import sys
import json
import os
from datetime import datetime

from .common import safe_get

def run_command_and_get_stdout(cmd: str, check=True):
    stdout = subprocess.run(
        cmd, 
        shell=True, 
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, 
        env=os.environ.copy()
    ).stdout
    return stdout.decode('utf-8', errors='ignore')

def truncate_string_in_byte_size(unicode_string: str, size: int):
    # byte_string = unicode_string.encode('utf-8')
    # limit = size
    # # 
    # while (byte_string[limit] & 0xc0) == 0x80:
    #   limit -= 1
    # return byte_string[:limit].decode('utf-8')
    if len(unicode_string.encode('utf8')) > size:
        return unicode_string.encode('utf8')[:size].decode('utf8', 'ignore').strip() + '...'
    return unicode_string


def install_streamlink(streamlink_github=None, streamlink_commit=None, streamlink_version=None):
    if streamlink_github:
        return run_command_and_get_stdout(f'''{sys.executable} -m pip install "git+{streamlink_github}"''')
    
    if streamlink_commit:
        return run_command_and_get_stdout(f'''{sys.executable} -m pip install "git+https://github.com/streamlink/streamlink.git@{streamlink_commit}"''')
    
    if streamlink_version:
        return run_command_and_get_stdout(f'''{sys.executable} -m pip install "streamlink=={streamlink_version}"''') 
    
    return run_command_and_get_stdout(f'''{sys.executable} -m pip install --upgrade streamlink''') 

def get_stream_info(target_url: str):
    return json.loads(
        run_command_and_get_stdout(
            f'''{sys.executable} -m streamlink --json {target_url}''',
            check=False,
        )
    )

def parse_metadata_from_stream_info(stream_info: dict) -> tuple:
    plugin = safe_get(stream_info, ["plugin"])
    metadata_id = safe_get(stream_info, ["metadata", "id"])
    metadata_author = safe_get(stream_info, ["metadata", "author"])
    metadata_category = safe_get(stream_info, ["metadata", "category"])
    metadata_title = safe_get(stream_info, ["metadata", "title"])
    return (plugin, metadata_id, metadata_author, metadata_category, metadata_title)

def is_online(stream_info: dict):
    return (safe_get(stream_info, 'error') is None and \
        safe_get(stream_info, ["metadata", "id"]) is not None)

def format_filepath(
    filepath_template: str, 
    plugin: str=None, 
    metadata_id: str=None, 
    metadata_author: str=None, 
    metadata_category: str=None, 
    metadata_title: str=None
) -> str:
    filepath = filepath_template
    filepath = filepath.replace('{plugin}', plugin)
    filepath = filepath.replace('{id}', metadata_id)
    filepath = filepath.replace('{author}', metadata_author)
    filepath = filepath.replace('{category}', metadata_category)
    
    # title could be too long
    do_truncate_title = False
    full_title_filepath = filepath.replace('{title}', metadata_title)
    for linkname in full_title_filepath.split('/'):
        if len(linkname.encode('utf-8', errors='ignore')) > 224:
            # 256 - 32
            do_truncate_title = True
            break
    if do_truncate_title:
        truncated_metadata_title = truncate_string_in_byte_size(metadata_title, 147)
        filepath = filepath.replace('{title}', truncated_metadata_title)
    else:
        filepath = filepath.replace('{title}', metadata_title)
    filepath = datetime.now().strftime(filepath)
    
    return filepath