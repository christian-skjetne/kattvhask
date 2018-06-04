import websockets


async def echo(websocket, path):
    print("New connection..")
    async for message in websocket:
        await websocket.send(message)


def get_server():
    return websockets.serve(echo, 'localhost', 6789)
