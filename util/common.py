import os
import subprocess
from typing import Union, List, Callable, Optional
from copy import deepcopy
import functools
import traceback
from datetime import datetime

import requests

from .logger import main_logger


def safe_get(
    data: Union[dict, list],
    key_list: Union[List[Union[str, int]], str, int],
    default=None,
):
    if not isinstance(key_list, list):
        return safe_get(data, [key_list], default=default)

    try:
        result = deepcopy(data)
        for key in key_list:
            result = result[key]
        return result
    except:
        return default


def silent_of(func: Callable) -> Callable:
    def __func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            main_logger.error(traceback.format_exc())

    return functools.update_wrapper(__func, func)


@silent_of
def send_discord_message(content: str, discord_webhook: str = None, username: str = None):
    if not discord_webhook:
        return

    data = {"content": content}
    if username:
        data["username"] = username

    response = requests.post(discord_webhook, json=data)
    response.raise_for_status()


def truncate_string_in_byte_size(unicode_string: str, size: int):
    # byte_string = unicode_string.encode('utf-8')
    # limit = size
    # #
    # while (byte_string[limit] & 0xc0) == 0x80:
    #   limit -= 1
    # return byte_string[:limit].decode('utf-8')
    if len(unicode_string.encode("utf8")) > size:
        return unicode_string.encode("utf8")[:size].decode("utf8", "ignore").strip() + "..."
    return unicode_string


def replace_unavailable_characters_in_filename(source: str):
    replace_list = {
        ":": "_",
        "/": "_",
        "\\": "_",
        "*": "_",
        "?": "_",
        '"': "'",
        "<": "(",
        ">": ")",
        "|": "_",
        "\n": " ",
        "\r": " ",
    }
    for key, value in replace_list.items():
        source = source.replace(key, value)
    return source


def format_filepath(
    filepath_template: str,
    plugin: str = None,
    metadata_id: str = None,
    metadata_author: str = None,
    metadata_category: str = None,
    metadata_title: str = None,
) -> str:
    if "/" in filepath_template:
        return "/".join(
            [
                format_filepath(
                    filename_template,
                    plugin=plugin,
                    metadata_id=metadata_id,
                    metadata_author=metadata_author,
                    metadata_category=metadata_category,
                    metadata_title=metadata_title,
                )
                for filename_template in filepath_template.split("/")
            ]
        )

    filepath = filepath_template
    filepath = filepath.replace("{plugin}", str(plugin))
    filepath = filepath.replace("{id}", str(metadata_id))
    filepath = filepath.replace("{author}", str(metadata_author))
    filepath = filepath.replace("{category}", str(metadata_category))

    # title could be too long
    do_truncate_title = False
    full_title_filepath = filepath.replace("{title}", str(metadata_title))
    for linkname in os.path.split(full_title_filepath):
        if len(linkname.encode("utf-8", errors="ignore")) > 224:
            # 256 - 32
            do_truncate_title = True
            break
    if do_truncate_title:
        truncated_metadata_title = truncate_string_in_byte_size(metadata_title, 147)
        filepath = filepath.replace("{title}", str(truncated_metadata_title))
    else:
        filepath = filepath.replace("{title}", str(metadata_title))
    filepath = datetime.now().strftime(filepath)
    filepath = replace_unavailable_characters_in_filename(filepath)

    return filepath


def get_output_of_command(command: List[str]) -> str:
    result = ""
    try:
        result = subprocess.check_output(
            command,
            encoding="utf-8",
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        result = e.output
    return result


def get_stdout_of_command(command: List[str]) -> Optional[str]:
    result = subprocess.check_output(
        command,
        encoding="utf-8",
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result
