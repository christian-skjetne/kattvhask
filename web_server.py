import websockets
import asyncio

# Store 50 events in queue

# QUEUE needs to be started inside the 'new_loop'
queue = None
# asyncio.Queue(maxsize=100)

async def events(websocket):
    async for message in websocket:
        await websocket.send(message)

async def echo(websocket, path):
    print("async echo ws")
    async for message in websocket:
        await websocket.send(message)

async def kattvhask_ws(websocket, path):
    print(f"New connection.. path -> {path}")

    # routes = {
    #     '/events': events,
    #     '/echo': echo
    # }
    #async for message in websocket:
    #    await websocket.send(message)
    print(f"websocket: {websocket}")
    try:
        while True:
            event = await queue.get()
            print(f"event: {event}")
            await websocket.send(str(event))
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed.")
    # if path not in routes:
    #     return

    # return await routes[path](websocket)


def get_server():
    print("Starting server")
    return websockets.serve(kattvhask_ws, 'localhost', 6789)

    # async with websockets.serve(echo, 'localhost', 6789):
    #     await stop

def start_server(loop):
    global queue
    asyncio.set_event_loop(loop)
    start_server_task = get_server()
    # asyncio.Queue(maxsize=100)
    queue = asyncio.Queue(maxsize=100, loop=loop)

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
