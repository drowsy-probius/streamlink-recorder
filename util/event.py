# topic and message pair 
# ("is_online", True)
# ("is_online", False)
# ("stream_info", stream_info)

import threading
from typing import Dict, List, Optional

from .logger import main_logger

class Subscriber:
    def __init__(self, name: str):
        self.name = name
        self.event = threading.Event()
        self.message = None

    def receive(self, timeout: Optional[float]):
        """you must call `.event.clear()` after done"""
        is_timed_out = self.event.wait(timeout)
        if is_timed_out:
            return None
        return self.message


class Publisher:
    def __init__(self):
        self.subscribers: Dict[str, List[Subscriber]] = {}

    def subscribe(self, subscriber: Subscriber, topic: str):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(subscriber)

    def publish(self, topic, message):
        main_logger.info("publish event %s: %s", topic, message)
        if topic in self.subscribers:
            for subscriber in self.subscribers[topic]:
                subscriber.message = message
                subscriber.event.set()
