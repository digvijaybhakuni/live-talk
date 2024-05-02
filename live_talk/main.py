from fastapi import FastAPI, WebSocket

from fastapi.staticfiles import StaticFiles

import live_talk.dependency as deps

from asyncio import Queue

import json
import uuid
import threading

from live_talk.connection_manager import ConnectionManager, my_worker
from live_talk.transcribe import load_whisper_model


services = {}


def init_app(app: FastAPI):
    print("starting")
    audio_model = load_whisper_model(model_id="tiny.en")
    services["audio_model"] = audio_model
    connection_manager = deps.get_connection_manager()
    services["connection_manager"] = connection_manager
    mythread = threading.Thread(
        target=my_worker,
        args=(
            connection_manager,
            audio_model,
        ),
        daemon=True,
    )
    mythread.start()
    print("started")
    yield


app = FastAPI(lifespan=init_app)
app.mount(path="/app", app=StaticFiles(directory="public"), name="ui")


@app.get("/api/ping")
async def ping():
    """
    API Test the health status using ping-pong
    """
    connection_manager: ConnectionManager = services["connection_manager"]
    info = str(connection_manager)
    return {"message": "pong", "info": info}


@app.websocket("/api/ws")
async def websocket_connect(websocket: WebSocket):
    """
    API to connect to websocket connection
    """
    connection_manager: ConnectionManager = services["connection_manager"]
    print("cm -> ", connection_manager)
    headers = websocket.headers
    print("headers ", headers)
    # await websocket.accept()
    client_id = str(uuid.uuid4())
    await connection_manager.connect(client_id=client_id, websocket=websocket)
    chunks = []
    while True:
        data = await websocket.receive()
        print("attr", data.keys())
        data_type = data["type"]
        print("data type", data_type)

        if "bytes" in data:
            data_bytes = data["bytes"]
            chunks.append(data_bytes)
            data_size = len(data_bytes)
            print("data size", data_size)
            # await websocket.send_text(f"Message Get data {data_size}")
            # await connection_manager.send_message(client_id=client_id, message=f'Message Get Data {data_size}')
            await connection_manager.put_data(client_id=client_id, data=data_bytes)
            # await user_queue.put(item=data_bytes)
            # msgs = message_queue.queue()
            # for msg in msgs:
            #     await websocket.send_text(msg)
        elif "text" in data:
            text = data["text"]
            json_msg = json.loads(text)
            print(json_msg)
            if json_msg["status"] == "STOP":
                print("write to file")
                file_uuid = uuid.uuid4()
                with open(f"temp/{str(file_uuid)}.opus", "wb") as f:
                    for c in chunks:
                        f.write(c)
        # if not message_queue.empty():
        # msg = await message_queue.get()
        # if msg:
        #     await websocket.send_text(msg)


if __name__ == "__main__":
    # threading.Thread(target=worker, args=(connection_manager,), daemon=True).start()
    import uvicorn

    uvicorn.run("main:app", port=8760, workers=2, reload=True)
