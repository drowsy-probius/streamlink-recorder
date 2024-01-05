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
        is_published = self.event.wait(timeout)
        if not is_published:
            return None
        main_logger.info("receive event %s: %s", self.name, str(self.message)[:100])
        return self.message


class Publisher:
    def __init__(self):
        self.subscribers: Dict[str, List[Subscriber]] = {}

    def subscribe(self, subscriber: Subscriber, topic: str):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(subscriber)

    def publish(self, topic, message):
        main_logger.info("publish event %s: %s", topic, str(message)[:100])
        if topic in self.subscribers:
            for subscriber in self.subscribers[topic]:
                subscriber.message = message
                subscriber.event.set()
