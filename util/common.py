import random
from typing import Union, List, Callable
from copy import deepcopy
import time
import functools
import traceback

import requests

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


def silent_of(
    func: Callable
) -> Callable:
    def __func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            traceback.print_exc()

    return functools.update_wrapper(__func, func)


@silent_of
def send_discord_message(content: str, discord_webhook: str=None, username: str = None):
    if not discord_webhook:
        return
    
    data = {
        "content": content
    }
    if username:
        data["username"] = username
    
    response = requests.post(discord_webhook, json=data)
    response.raise_for_status()
