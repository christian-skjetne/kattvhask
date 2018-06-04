import websockets
import queue

# Store 50 events in queue
queue = queue.Queue(maxsize=50)


async def events(websocket):
    async for message in websocket:
        await websocket.send(message)

async def echo(websocket):
    async for message in websocket:
        await websocket.send(message)

async def kattvhask_ws(websocket, path):
    print(f"New connection.. path -> {path}")

    routes = {
        '/events': events,
        '/echo': echo
    }
    async for message in websocket:
        await websocket.send(message)
    # if path not in routes:
    #     return

    # return await routes[path](websocket)


async def get_server(stop):
    return websockets.serve(echo, 'localhost', 6789)
    # async with websockets.serve(echo, 'localhost', 6789):
    #     await stop
