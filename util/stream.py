import subprocess
import sys
import json
import os


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

