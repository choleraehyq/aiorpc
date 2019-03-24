# -*- coding: utf-8 -*-
import time
import aiorpc
import asyncio
import uvloop
import multiprocessing

NUM_CALLS = 10000


def run_sum_server():
    def sum(x, y):
        return x + y

    aiorpc.register('sum', sum)
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    coro = asyncio.start_server(aiorpc.serve, 'localhost', 6000, loop=loop)
    loop.run_until_complete(coro)
    loop.run_forever()


def call():
    async def do(cli):
        for i in range(NUM_CALLS):
            await cli.call('sum', 1, 2)
            # print('{} call'.format(i))
    client = aiorpc.RPCClient('localhost', 6000)
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    start = time.time()

    loop.run_until_complete(do(client))

    print('call: %d qps' % (NUM_CALLS / (time.time() - start)))


if __name__ == '__main__':
    p = multiprocessing.Process(target=run_sum_server)
    p.start()

    time.sleep(1)

    call()

    p.terminate()
