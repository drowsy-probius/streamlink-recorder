import sys
import json

from .common import run_command_and_get_stdout

def install_streamlink(streamlink_github=None, streamlink_commit=None, streamlink_version=None):
    if streamlink_github:
        return run_command_and_get_stdout(
            f'''{sys.executable} -m pip install --upgrade --force-reinstall "git+{streamlink_github}"'''
        )
    
    if streamlink_commit:
        return run_command_and_get_stdout(
            f'''{sys.executable} -m pip install --upgrade --force-reinstall "git+https://github.com/streamlink/streamlink.git@{streamlink_commit}"'''
        )
    
    if streamlink_version:
        return run_command_and_get_stdout(
            f'''{sys.executable} -m pip install --force-reinstall "streamlink=={streamlink_version}"'''
        ) 
    
    return run_command_and_get_stdout(
        f'''{sys.executable} -m pip install --upgrade --force-reinstall streamlink'''
    ) 


def get_stream_info(target_url: str):
    return json.loads(
        run_command_and_get_stdout(
            f'''{sys.executable} -m streamlink --json {target_url}''',
            check=False,
        )
    )

