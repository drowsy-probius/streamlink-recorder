# multithread-safe, but not multiprocessing-safe

from datetime import datetime, timezone
import logging
from logging.handlers import TimedRotatingFileHandler
import os

raw_formatter = logging.Formatter(fmt="%(message)s")

class _TimezoneFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.astimezone()

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec="milliseconds")
            except TypeError:
                s = dt.isoformat()
        return s


class _CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    light_green = "\x1b[92m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    COLORS = {
        logging.DEBUG: grey,
        logging.INFO: light_green,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }

    def __init__(
        self,
        name,
        fmt: str = None,
        datefmt: str = None,
        style: str = "%",
        validate: bool = True,
        use_color: bool = True,
    ) -> None:
        super().__init__(fmt, datefmt, style, validate)
        self.name = name
        self.use_color = use_color

    def format_message(self, levelno):
        return (
            (self.COLORS.get(levelno) if self.use_color else "")
            + "[%(asctime)s]["
            + self.name
            + "][%(levelname)s][%(process)s] %(message)s"
            + (self.reset if self.use_color else "")
            + "\n\t(%(pathname)s:%(lineno)d (%(funcName)s)"
        )

    def format(self, record):
        message_format = self.format_message(record.levelno)
        formatter = _TimezoneFormatter(message_format)
        return formatter.format(record)


def __get_file_handler(name: str, log_dir: str):
    filename = f"{name}.log"
    filepath = os.path.join(log_dir, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    os.system(f'sudo chown -R abc:abc "{os.path.dirname(filepath)}"')

    file_handler = TimedRotatingFileHandler(
        filename=filepath, 
        when='d', 
        interval=1, 
        backupCount=90,
        encoding='utf-8', 
        delay=True, 
        errors='ignore',
    )
    file_handler.suffix = "-%Y%m%d"
    file_handler.setLevel(logging.INFO)
    return file_handler


def get_logger(name: str, custom_format=True):
    log_dir = os.path.realpath('/log')

    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    if custom_format:
        stream_handler.setFormatter(_CustomFormatter(name))
    else:
        stream_handler.setFormatter(raw_formatter)
    logger.handlers = [stream_handler]

    file_handler = __get_file_handler(name, log_dir=log_dir)
    if custom_format:
        file_handler.setFormatter(_CustomFormatter(name, use_color=False))
    else:
        file_handler.setFormatter(raw_formatter)
    logger.addHandler(file_handler)

    return logger

main_logger = get_logger('main')
subprocess_logger = get_logger('subprocess', custom_format=False)