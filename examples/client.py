from aiorpc import RPCClient

import asyncio
import uvloop

async def do(cli):
    ret = await client.call('echo', 'message')
    print("|||||||||fuck {}||||||||\n".format(ret))

loop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)
client = RPCClient('127.0.0.1', 6000)
loop.run_until_complete(do(client))
client.close()
