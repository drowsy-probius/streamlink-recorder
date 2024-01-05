import sys
import json

from .common import run_command_and_get_stdout
from .logger import main_logger

def install_streamlink(streamlink_github=None, streamlink_commit=None, streamlink_version=None):
    if streamlink_github:
        main_logger.info('install streamlink from %s', streamlink_github)
        return run_command_and_get_stdout(
            f'''{sys.executable} -m pip install --upgrade --force-reinstall "git+{streamlink_github}"'''
        )
    
    if streamlink_commit:
        main_logger.info('install streamlink from %s', streamlink_commit)
        return run_command_and_get_stdout(
            f'''{sys.executable} -m pip install --upgrade --force-reinstall "git+https://github.com/streamlink/streamlink.git@{streamlink_commit}"'''
        )
    
    if streamlink_version:
        main_logger.info('install streamlink %s', streamlink_version)
        return run_command_and_get_stdout(
            f'''{sys.executable} -m pip install --force-reinstall "streamlink=={streamlink_version}"'''
        ) 
    
    main_logger.info('install the latest streamlink')
    return run_command_and_get_stdout(
        f'''{sys.executable} -m pip install --upgrade --force-reinstall streamlink'''
    ) 


def get_stream_info(target_url: str, streamlink_args: str):
    command = f'''{sys.executable} -m streamlink --json "{target_url}" {streamlink_args}'''
    main_logger.debug(command)
    result = run_command_and_get_stdout(command, check=False)
    result_json = {}
    try:
        result_json = json.loads(result)
    except Exception as e:
        raise Exception(result) from e
    if result_json.get("error", None) is not None:
        raise Exception(result_json)
    return result_json

