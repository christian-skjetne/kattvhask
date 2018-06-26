import websockets
import asyncio
import json

# Store 50 events in queue
queue = None
frames = None

# List of connected clients
connected = set()

async def events(websocket):
    async for message in websocket:
        await websocket.send(message)

async def get_frames():
    await frames.get()

async def consume(message):
    """Validate input regions created from the web interface"""
    print(message)
    return True

async def read_user_input(websocket):
    async for message in websocket:
        await consume(message)

async def stream_frames(websocket, path):
    if path.startswith("/frames"):
        while True:
            frame = await frames.get()
            if frame is not None:
                if websocket.open:
                    await websocket.send(frame.decode("utf-8"))

async def stream_events(websocket, path):
    connected.add(websocket)
    # cmd = await websocket.recv()
    # if not cmd.startswith("CONN"):
    #     await websockets.send("Bad command")
    #     return
    try:
        # start with pushin the current camera setup
        current_setup = dict(regions=[(1,1), (255,255)])
        await websocket.send(json.dumps(current_setup))

        while True:
            event = await queue.get()
            print(f"event: {event}")
            await websocket.send(str(event))
    finally:
        # Unregister
        connected.remove(websocket)

async def kattvhask_ws(websocket, path):
    if websocket in connected:
        print(f"Already registered client")

    # frame_streamer_task = asyncio.ensure_future(
    #     stream_frames(websocket, path))
    if path.startswith('/frames'):
        print("Client connected for streaming frames..")
        stream_frame_task = asyncio.ensure_future(stream_frames(websocket, path))
        await stream_frame_task
        return

    print("Client connected for streaming events")

    input_reader_task = asyncio.ensure_future(
        read_user_input(websocket)
    )
    event_streamer = asyncio.ensure_future(
        stream_events(websocket, path)
    )

    done, pending = await asyncio.wait(
        [input_reader_task, event_streamer],
        return_when=asyncio.FIRST_COMPLETED,
    )
    print("done and pending")
    print(done)
    for task in pending:
        task.cancel()

def get_server():
    print("Starting server")
    return websockets.serve(kattvhask_ws, 'localhost', 6789)

    # async with websockets.serve(kattvhask_ws, 'localhost', 6789):
    #     await stop

def start_server(loop):
    global queue, frames
    asyncio.set_event_loop(loop)
    start_server_task = get_server()

    # setup asyncio queues
    queue = asyncio.Queue(maxsize=100, loop=loop)
    frames = asyncio.Queue(maxsize=100, loop=loop)

    server = loop.run_until_complete(start_server_task)
    loop.run_forever()
    print("Loop exited. Closing server..")
    server.close()
    loop.run_until_complete(server.wait_closed())

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_server())
    loop.run_forever()
