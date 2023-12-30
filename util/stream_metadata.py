from datetime import datetime
import threading
import time
import traceback
from copy import deepcopy
import logging

from .stream import get_stream_info, parse_metadata_from_stream_info, is_online

logger = logging.getLogger()


class StreamMetadata:
    target_url: str
    is_stop = False
    is_online = False
    thread = None
    stack = []
    
    def __init__(self, target_url: str) -> None:
        self.target_url = target_url
        self.set_metadata()
        if not self.is_online:
            return
        
        self.thread = threading.Thread(target=self.set_metadata_loop)
        self.thread.daemon = True 
        self.thread.start()
    
    def destroy(self):
        self.is_stop = True
        self.thread.join()
    
    def set_metadata_loop(self):
        while not self.is_stop:
            self.set_metadata()
            time.sleep(15)
    
    def set_metadata(self):
        try:
            stream_info = get_stream_info(self.target_url)
        
            current_is_online = is_online(stream_info)
            if self.is_online != current_is_online:
                self.stack = []
            self.is_online = current_is_online
            
            if not self.is_online:
                return

            (
                plugin, 
                metadata_id, 
                metadata_author, 
                metadata_category, 
                metadata_title
            ) = parse_metadata_from_stream_info(stream_info)
            
            if not self.stack:
                self.stack.append({
                    'plugin': plugin,
                    'id': metadata_id,
                    'author': metadata_author,
                    'category': metadata_category,
                    'title': metadata_title,
                    'timestamp': datetime.now().strftime('%Y%m%dT%H%M%S.%f%z'),
                    'datetime': datetime.now().strftime('%Y%m%d_%H%M%S')
                })
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

            print('update metadata', flush=True)

            self.stack.append({
                'plugin': plugin,
                'id': metadata_id,
                'author': metadata_author,
                'category': metadata_category,
                'title': metadata_title,
                'timestamp': datetime.now().strftime('%Y%m%dT%H%M%S.%f%z')
            })
        except:
            traceback.print_exc()
            
    
    def get_latest_metadata(self):
        return deepcopy(self.stack[-1])