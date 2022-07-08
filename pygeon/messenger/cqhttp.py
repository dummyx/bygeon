from .messenger import Messenger
import websocket
from websocket import WebSocketApp as WSApp
from hub import Hub
from message import Message, Attachment
import threading
import orjson
import requests

from typing import TypedDict, List
from enum import Enum
import util


class PostType(Enum):
    META_EVENT = "meta_event"
    MESSAGE = "message"
    NOTICE = "notice"


class MetaEventType(Enum):
    HEARTBEAT = "heartbeat"


class MessageType(Enum):
    GROUP = "group"


class Sender(TypedDict):
    nickname: str
    user_id: int


class CQData(TypedDict):
    id: str
    text: str


class CQMessage(TypedDict):
    type: str
    data: CQData


class WSMessage(TypedDict):
    post_type: str
    meta_event_type: str
    message_type: str
    sender: Sender
    message_id: str
    message: List[CQMessage]


class CQHttp(Messenger):
    @property
    def gateway_url(self) -> str:
        return "ws://localhost:8080/"

    @property
    def api_url(self) -> str:
        return "http://localhost:8081/send_group_msg"

    @property
    def recall_url(self) -> str:
        return "http://localhost:8081/delete_msg"

    def __init__(self, group_id: str, hub: Hub) -> None:
        self.group_id = int(group_id)
        self.hub = hub
        self.logger = self.get_logger()

    def on_open(self, ws) -> None:
        # TODO
        ...

    def on_error(self, ws, e) -> None:
        # TODO
        ...

    def on_close(self, ws, close_status_code, close_msg) -> None:
        # TODO
        ...

    def on_message(self, ws: WSApp, message: str):
        ws_message: WSMessage = orjson.loads(message)
        post_type = ws_message["post_type"]
        is_reply = False
        message_group_id = ws_message.get("group_id")
        match PostType(post_type):
            case PostType.MESSAGE:
                if message_group_id != self.group_id:
                    return None
                message_id = ws_message["message_id"]
                author = ws_message["sender"]["nickname"]

                data = ws_message["message"]
                text = ""
                attachments = []
                for d in data:
                    if d["type"] == "reply":
                        is_reply = True
                        ref_id = d["data"]["id"]
                    elif d["type"] == "text":
                        text += d["data"]["text"]
                    elif d["type"] == "image":
                        url = d["data"]["url"]
                        filename = d["data"]["file"]
                        filename = f"{self.name}_{filename}"
                        path = self.generate_cache_path(self.hub.name)
                        file_path = util.download_to_cache(url, path, filename)
                        attachments.append(Attachment("image", file_path))
                m = Message(self.name, message_id, author, text, attachments)
                if is_reply:
                    self.hub.reply_message(m, ref_id)
                else:
                    self.hub.new_message(m)
            case PostType.NOTICE:
                recalled_id = ws_message["message_id"]
                self.hub.recall_message(self.name, recalled_id)
                ...

    def recall_message(self, message_id: str) -> None:
        payload = {
            "message_id": message_id,
        }
        r = requests.post(self.recall_url, json=payload)
        self.logger.info("Trying to recall: " + message_id)
        self.logger.info(r.json())

    def reconnect(self) -> None:
        ...

    def send_reply(self, message: Message, ref_id: str) -> None:
        payload = {
            "group_id": self.group_id,
            "message": f"[CQ:reply,id={ref_id}] {message.text}",
        }
        r = requests.post(self.api_url, json=payload)
        response = r.json()
        self.hub.update_entry(message, self.name, response["data"]["message_id"])
        self.logger.error(r.json())

    def send_message(self, message: Message) -> None:
        payload = {
            "group_id": self.group_id,
            "message": "",
        }
        for attachment in message.attachments:
            payload["message"] += f"[CQ:{attachment.type},file=file:{attachment.file_path}]"
        payload["message"] += f"[{message.author_username}]: {message.text}"
        self.logger.info(payload)

        r = requests.post(self.api_url, json=payload)
        self.logger.info(r.text)

        response = r.json()
        self.hub.update_entry(message, self.name, response["data"]["message_id"])

    def start(self) -> None:
        self.ws = websocket.WebSocketApp(
            self.gateway_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()

    def join(self) -> None:
        self.thread.join()
