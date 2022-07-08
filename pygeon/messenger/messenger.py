from typing import Protocol
from message import Message
import os
import colorlog as cl
import logging

handler = cl.StreamHandler()
handler.setFormatter(
    cl.ColoredFormatter("%(log_color)s%(levelname)s: %(name)s: %(message)s")
)
logger = cl.getLogger("Discord")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger_format = "%(log_color)s%(levelname)s: %(name)s: %(message)s"


class Messenger(Protocol):
    logger: logging.Logger

    def get_logger(self):
        handler = cl.StreamHandler()
        handler.setFormatter(cl.ColoredFormatter(logger_format))

        logger = cl.getLogger(self.name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        return logger

    @property
    def file_cache_path(self) -> str:
        return os.path.join(os.getcwd(), "file_cache")

    def generate_cache_file_path(self, filename: str) -> str:
        return os.path.join(self.file_cache_path, filename)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def send_message(self, message: Message) -> None:
        ...

    def send_reply(self, message: Message, ref_id: str) -> None:
        ...

    def recall_message(self, message_id: str) -> None:
        ...

    def start(self) -> None:
        ...

    def join(self) -> None:
        ...
