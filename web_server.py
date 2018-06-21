import websockets
import asyncio

# Store 50 events in queue

# QUEUE needs to be started inside the 'new_loop'
queue = None
frames = None

# List of connected clients
connected = set()

async def events(websocket):
    async for message in websocket:
        await websocket.send(message)

async def get_frames():
    await frames.get()

async def kattvhask_ws(websocket, path):
    print(f"New connection.. path -> {path}")

    if websocket in connected:
        print(f"Already registered client")

    if path.startswith("/frames"):
        while True:
            frame = await frames.get()
            if frame is None:
                print("WTF? Frame is None...")
                return
            await websocket.send(frame.decode("utf-8"))
    else:
        connected.add(websocket)

        # cmd = await websocket.recv()
        # if not cmd.startswith("CONN"):
        #     await websockets.send("Bad command")
        #     return
        """
        dir(websocket): ['AbortHandshake', 'ConnectionClosed', 'DuplicateParameter', 'InvalidHandshake', 'InvalidHeader', 'InvalidHeaderFormat', 'InvalidHeaderValue', 'InvalidMessage', 'InvalidOrigin', 'InvalidParameterName', 'InvalidParameterValue', 'InvalidState', 'InvalidStatusCode', 'InvalidURI', 'InvalidUpgrade', 'NegotiationError', 'PayloadTooBig', 'WebSocketClientProtocol', 'WebSocketCommonProtocol', 'WebSocketProtocolError', 'WebSocketServerProtocol', 'WebSocketURI', '__all__', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', '__version__', 'client', 'compatibility', 'connect', 'exceptions', 'extensions', 'framing', 'handshake', 'headers', 'http', 'parse_uri', 'protocol', 'py36', 'serve', 'server', 'speedups', 'unix_serve', 'uri', 'version']
        websocket: <websockets.server.WebSocketServerProtocol object at 0x7f2eef5eaf98>
        """
        try:
            while True:
                event = await queue.get()
                print(f"event: {event}")
                await websocket.send(str(event))
        finally:
            # Unregister
            connected.remove(websocket)

    # if path not in routes:
    #     return

    # return await routes[path](websocket)


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
