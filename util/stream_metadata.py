import threading
import time
import traceback
import logging
import gc
from datetime import datetime, timezone
from copy import deepcopy
from typing import List, Tuple

from .event import Publisher, Subscriber
from .common import safe_get
from .stream import get_stream_info
from .logger import main_logger

logger = logging.getLogger()

def is_online(stream_info: dict):
    return (safe_get(stream_info, 'error') is None and \
        safe_get(stream_info, ["metadata", "id"]) is not None)


def parse_metadata_from_stream_info(stream_info: dict) -> tuple:
    plugin = safe_get(stream_info, ["plugin"])
    metadata_id = safe_get(stream_info, ["metadata", "id"])
    metadata_author = safe_get(stream_info, ["metadata", "author"])
    metadata_category = safe_get(stream_info, ["metadata", "category"])
    metadata_title = safe_get(stream_info, ["metadata", "title"])
    return (plugin, metadata_id, metadata_author, metadata_category, metadata_title)


class StreamMetadata:
    publisher: Publisher
    target_url: str
    streamlink_args: str
    check_interval: float
    is_stop = False
    is_online = False
    thread = None
    stack = []
    stack_raw = []
    latest_stack = []
    latest_stack_raw = []
    
    def __init__(self, target_url: str, streamlink_args: str, check_interval: float, subscribers: List[Tuple[Subscriber, str]] = []) -> None:
        self.publisher = Publisher()
        for subscriber, topic in subscribers:
            self.add_subscriber(subscriber, topic)

        self.target_url = target_url
        self.streamlink_args = streamlink_args
        self.check_interval = check_interval
        self.thread = threading.Thread(target=self.set_metadata_loop)
        self.thread.daemon = True 
        self.thread.start()

    def __del__(self):
        self.destroy()

    def add_subscriber(self, subscriber: Subscriber, topic: str):
        self.publisher.subscribe(subscriber, topic)

    def destroy(self):
        self.is_stop = True
        if self.thread is not None:
            self.thread.join()

    def set_metadata_loop(self):
        while not self.is_stop:
            gc.collect()
            self.set_metadata()
            if not self.is_online:
                main_logger.debug('sleep')
            time.sleep(self.check_interval)
    
    def set_metadata(self):
        try:
            stream_info = get_stream_info(self.target_url, self.streamlink_args)
            current_is_online = is_online(stream_info)
            
            if current_is_online == False:
                if self.is_online:
                    self.latest_stack = self.stack
                    self.latest_stack_raw = self.stack_raw
                    self.publisher.publish("is_online", False)
                self.stack = []
                self.stack_raw = []
                self.is_online = current_is_online
                return

            # current_is_online is True

            if self.is_online == False:
                # new stream starts
                self.publisher.publish("is_online", True)
                self.latest_stack = []
                self.latest_stack_raw = []
                
            self.is_online = current_is_online

            (
                plugin, 
                metadata_id, 
                metadata_author, 
                metadata_category, 
                metadata_title
            ) = parse_metadata_from_stream_info(stream_info)
            
            if not self.stack:
                self.stack_raw.append(stream_info)
                self.stack.append({
                    'plugin': plugin,
                    'id': metadata_id,
                    'author': metadata_author,
                    'category': metadata_category,
                    'title': metadata_title,
                    'timestamp': datetime.now(timezone.utc).astimezone().strftime('%Y%m%dT%H%M%S%z'),
                    'datetime': datetime.now().strftime('%Y%m%d_%H%M%S')
                })
                self.latest_stack = self.stack
                self.latest_stack_raw = self.stack_raw
                self.publisher.publish("stream_info", stream_info)
                return
            
            latest_metadata = self.stack[-1]
            if (
                latest_metadata['plugin'] == plugin and \
                latest_metadata['id'] == metadata_id and \
                latest_metadata['author'] == metadata_author and \
                latest_metadata['category'] == metadata_category and \
                latest_metadata['title'] == metadata_title
            ):
                return

            self.stack_raw.append(stream_info)
            self.stack.append({
                'plugin': plugin,
                'id': metadata_id,
                'author': metadata_author,
                'category': metadata_category,
                'title': metadata_title,
                'timestamp': datetime.now(timezone.utc).astimezone().strftime('%Y%m%dT%H%M%S%z'),
                'datetime': datetime.now().strftime('%Y%m%d_%H%M%S')
            })
            self.latest_stack = self.stack
            self.latest_stack_raw = self.stack_raw
            self.publisher.publish("stream_info", stream_info)
            main_logger.info("update metadata: %s", self.stack[-1])
        except:
            main_logger.error(traceback.format_exc())

    def get_latest_metadata(self):
        return deepcopy(self.latest_stack[-1])

    def get_stream_types(self):
        metadata = self.latest_stack_raw[-1]
        streams_dict = safe_get(metadata, ['streams'], {})
        streams_types = streams_dict.keys()
        return streams_types

