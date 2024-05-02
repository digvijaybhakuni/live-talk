import asyncio
from uuid import uuid4
from fastapi import WebSocket
from live_talk.transcribe import transcibe_data

# from redis import Redis, connection
# from rq import Queue

import queue
import time
import whisper

import logging

logger = logging.getLogger(__name__)


class ConnectionManager:

    def __init__(self) -> None:
        logger.info("Creating Connection Manager")
        self.id = str(uuid4())
        self.connection_dict: dict[str, WebSocket] = {}
        # self.redis = Redis.from_url("redis://localhost:6379/")
        # self.data_queue = Queue('data_queue', connection=self.redis)
        self.data_queue = queue.Queue(maxsize=500)

    async def connect(self, client_id: str, websocket: WebSocket):
        logger.info("Connect with Client_Id: %s", client_id)
        await websocket.accept()
        # Added add_connections
        self.add_connection(client_id=client_id, websocket=websocket)

    async def disconnect(self, client_id: str, websocket: WebSocket):
        if client_id in self.connection_dict:
            del self.connection_dict[client_id]

    def add_connection(self, client_id: str, websocket: WebSocket):
        logger.info("Added Websocket Connection for %s", client_id)
        self.connection_dict[client_id] = websocket

    async def put_data(self, client_id: str, data: bytes):
        # item = {'client_id': client_id, 'data': base64.b64encode(data).decode('utf-8')}
        item = {"client_id": client_id, "data": data}
        # print(item)

        self.data_queue.put(item)


    async def send_message(self, client_id: str, message: str):
        ws = self.connection_dict.get(client_id)
        if ws:
            await ws.send_text(message)
            logger.debug("Message Sent to Client_Id: %s ", client_id)
        else:
            logger.info("Client_Id : %s not found fail to send message", client_id)

    def get_next(self):
        return self.data_queue.get()

    def get_buffer(self):
        mapped = list(map(lambda x: x["data"], self.data_queue.queue))
        return b"".join(mapped)

    def data_empty(self):
        return self.data_queue.empty()

    def __str__(self) -> str:
        return f"ConnectionManager Class Id {self.id}"


def process(data, audio_model):
    print("process data")
    try:
        res = transcibe_data(audio_bytes=data["data"], audio_model=audio_model)
        print("response ", res)
        if res:
            return str(res)
    except Exception as e:
        print("error", e)

    return f"Recieve Data from {data['client_id']} with size {len(data['data'])}"


def on_success(message: str):
    print(message)


# def listen():
#     print('start listening')
#     with Redis.from_url("redis://localhost:6379/") as client:
#         pubsub = client.pubsub()
#         pubsub.subscribe("input_process")
#         for message in pubsub.listen():
#             if message["type"] == "message":
#                 print(message['data'])
#                 data = json.loads(message['data'])
#                 client_id = data['client_id']
#                 datab = base64.b64decode(data['data'])
#                 msg = process({'client_id': client_id, 'data': datab})
#                 print(msg)


def my_worker(conn_mgr: ConnectionManager, audio_model: whisper.Whisper):
    print("connection_manager ", conn_mgr)
    while True:
        time.sleep(5)
        item = conn_mgr.get_next()
        if item:
            message = process(item, audio_model)
            asyncio.run(
                conn_mgr.send_message(client_id=item["client_id"], message=message)
            )


# threading.Thread(target=listen, daemon=True).start()

# async def worker():
#     import time
#     while True:
#         time.sleep(5)
#         # data = asyncio.run(connection_manager.get_next())
#         redis = Redis.from_url("redis://localhost:6379/")
#         data_queue = Queue('data_queue', connection=self.redis)
#         data = await data_queue.get()
#         print(f"Recieve Data from {data['client_id']} with size {len(data['data'])}")
