import sys
import json
import subprocess

from .logger import main_logger

IS_INSTALL_STREAMLINK_PRINTED = False
IS_GET_STREAM_INFO_PRINTED = False

def install_streamlink(streamlink_github=None, streamlink_commit=None, streamlink_version=None):
    global IS_INSTALL_STREAMLINK_PRINTED
    
    command = [
        sys.executable,
        '-m', 'pip', 'install',
        '--upgrade', '--force-reinstall'
    ]
    
    if streamlink_github:
        if not IS_INSTALL_STREAMLINK_PRINTED:
            IS_INSTALL_STREAMLINK_PRINTED = True
            main_logger.info('install streamlink from %s', streamlink_github)
        command += [f'git+{streamlink_github}']
        return subprocess.check_output(command, encoding='utf-8', stderr=subprocess.STDOUT)
    
    if streamlink_commit:
        if not IS_INSTALL_STREAMLINK_PRINTED:
            IS_INSTALL_STREAMLINK_PRINTED = True
            main_logger.info('install streamlink from %s', streamlink_commit)
        command += [f'git+https://github.com/streamlink/streamlink.git@{streamlink_commit}']
        return subprocess.check_output(command, encoding='utf-8', stderr=subprocess.STDOUT)

    
    if streamlink_version:
        if not IS_INSTALL_STREAMLINK_PRINTED:
            IS_INSTALL_STREAMLINK_PRINTED = True
            main_logger.info('install streamlink %s', streamlink_version)
        command += [f'streamlink=={streamlink_version}']
        return subprocess.check_output(command, encoding='utf-8', stderr=subprocess.STDOUT)
    
    if not IS_INSTALL_STREAMLINK_PRINTED:
        IS_INSTALL_STREAMLINK_PRINTED = True
        main_logger.info('install the latest streamlink')
    command += ['streamlink']
    return subprocess.check_output(command, encoding='utf-8', stderr=subprocess.STDOUT)


def get_stream_info(target_url: str, streamlink_args: str):
    global IS_GET_STREAM_INFO_PRINTED
    
    command = [
        sys.executable,
        '-m',
        'streamlink',
        '--json',
        target_url,
        streamlink_args
    ]

    if not IS_GET_STREAM_INFO_PRINTED:
        IS_GET_STREAM_INFO_PRINTED = True
        main_logger.debug(command)

    result = subprocess.check_output(
        command, 
        encoding='utf-8', 
        stderr=subprocess.STDOUT
    )
    result_json = {}
    try:
        result_json = json.loads(result)
    except Exception as e:
        main_logger.error(f"{result}\n{e}")
        return result_json
        
    error_message = result_json.get("error", "")
    if error_message and "No playable streams found" not in error_message:
        main_logger.warning(error_message)

    return result_json

