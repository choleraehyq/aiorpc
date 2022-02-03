from aiorpc import register, serve

import asyncio
import uvloop


def echo(msg):
    return msg

def get_dict():
    return {1: 2}

loop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)
register("echo", echo)
register("get_dict", get_dict)
coro = asyncio.start_server(serve, '127.0.0.1', 6000, loop=loop)
server = loop.run_until_complete(coro)

try:
    loop.run_forever()
except KeyboardInterrupt:
    server.close()
    loop.run_until_complete(server.wait_closed())
