import websockets
import asyncio
import json
import typing
import threading
import janus

class GlobalSetup:
    """Global setup object to be shared between kattvhask and the websocket server. The intent is
    to support updates from either side and properly communicate them across asyncio/threads.

    Follows a basic Observer pattern.
    """
    def __init__(self):
        self._rectangles = []
        self._observers: typing.List[typing.Callable] = []
        self._lock = threading.Lock()

    @property
    def rectangles(self):
        return self._rectangles

    @rectangles.setter
    def rectangles(self, rectangles):
        with self._lock:
            self._rectangles = rectangles

        print("GlobalSetup announce changes!")
        self.announce()

    def add_rectangle(self, rect):
        with self._lock:
            self._rectangles.append(rect)
        self.announce()

    def rm_rectangle(self, rect):
        with self._lock:
            self._rectangles.remove(rect)
        self.announce()

    def announce(self):
        for callback in self._observers:
            callback(self._rectangles)

    def bind_to(self, callback: typing.Callable):
        print("Binding new callback to GlobalSetup")
        self._observers.append(callback)

    def remove_bind(self, callback: typing.Callable):
        self._observers.remove(callback)

    def json(self):
        output_obj = {
            "rectangles": self.rectangles,
            "type": "config"
        }
        return json.dumps(output_obj)

kattvhask_setup = GlobalSetup()
setup_queue = None
latest_setup = None

# Store 50 events in queue
queue = None
frames = None

# List of connected clients
connected = set()
connected_frames = set()

async def events(websocket):
    async for message in websocket:
        await websocket.send(message)

async def get_frames():
    await frames.get()

async def consume(message):
    """Validate input regions created from the web interface"""
    try:
        obj = json.loads(message)
        # kattvhask_setup.rectangles = obj
        setup_queue.put(obj)
    except json.JSONDecodeError:
        print(f"Unable to parse JSON: {message}")
        return False
    return True

async def read_user_input(websocket):
    async for message in websocket:
        await consume(message)

async def broadcast_frames(data):
    for ws in connected_frames:
        if ws.open:
            await ws.send(data)

async def broadcast_events(data):
    for ws in connected:
        if ws.open:
            await ws.send(data)

async def stream_frames(websocket, path):
    if path.startswith("/frames"):
        connected_frames.add(websocket)
        try:
            while True:
                frame = await frames.get()
                if frame is not None:
                    # if websocket.open:
                    #     await websocket.send(frame.decode("utf-8"))
                    await broadcast_frames(frame.decode("utf-8"))
        finally:
            connected_frames.remove(websocket)

async def stream_events(websocket, path):
    connected.add(websocket)
    try:
        # start with pushin the current camera setup
        # await websocket.send(kattvhask_setup.json())

        while True:
            event = await queue.get()
            print(f"event: {event}")
            await broadcast_events(json.dumps(event))
    finally:
        # Unregister
        connected.remove(websocket)

async def stream_setup(websocket, path):
    global latest_setup
    try:
        # start with pushin the current camera setup
        # await websocket.send(kattvhask_setup.json())
        async_queue = setup_queue.async_q

        if async_queue.empty() and latest_setup is not None:
            print(f" Pushing latest setup to new client..")
            await websocket.send(json.dumps(latest_setup))

        while True:
            event = await async_queue.get()
            latest_setup = event
            async_queue.task_done()
            print(f"setup event: {event}")
            await broadcast_events(json.dumps(event))
    finally:
        pass

async def kattvhask_ws(websocket, path):
    if websocket in connected:
        print(f"Already registered client")

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
    setup_streamer = asyncio.ensure_future(
        stream_setup(websocket, path)
    )

    done, pending = await asyncio.wait(
        [input_reader_task, event_streamer, setup_streamer],
        return_when=asyncio.FIRST_COMPLETED,
    )
    print("done and pending")
    print(done)
    for task in pending:
        task.cancel()

def get_server():
    print("Starting server")
    return websockets.serve(kattvhask_ws, 'localhost', 6789)


def start_server(loop, ws_ready_trigger):
    global queue, frames, setup_queue
    asyncio.set_event_loop(loop)
    start_server_task = get_server()

    # setup asyncio queues
    queue = asyncio.Queue(maxsize=100, loop=loop)
    frames = asyncio.Queue(maxsize=100, loop=loop)
    setup_queue = janus.Queue(loop=loop)

    # Send "ready" signal back to calling thread
    ws_ready_trigger.set()

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
