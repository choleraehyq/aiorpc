# -*- coding: utf-8 -*-


import asyncio

from nose.tools import *
import uvloop

from aiorpc import RPCClient, register, serve
from aiorpc.exceptions import RPCError

HOST = 'localhost'
PORT = 6000
loop = None
server = None


def setup_module():
    print("setup")
    set_up_server()


def teardown_module():
    print("teardown")
    server.close()
    loop.run_until_complete(server.wait_closed())


def echo(msg):
    return msg


async def echo_delayed(msg, delay):
    await asyncio.sleep(delay)
    return msg


def raise_error():
    raise Exception('error msg')


def set_up_server():
    global loop, server
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    register('echo', echo)
    register('echo_delayed', echo_delayed)
    register('raise_error', raise_error)
    coro = asyncio.start_server(serve, HOST, PORT)
    server = loop.run_until_complete(coro)


def test_call():
    async def _test_call():
        client = RPCClient(HOST, PORT)

        ret = await client.call('echo', 'message')
        eq_('message', ret)

        ret = await client.call('echo', 'message' * 100)
        eq_('message' * 100, ret)
        client.close()
    loop.run_until_complete(_test_call())


@raises(RPCError)
def test_call_server_side_exception():
    async def _test_call_server_side_exception():
        client = RPCClient(HOST, PORT)

        try:
            ret = await client.call('raise_error')
        except RPCError as e:
            eq_('error msg', str(e))
            raise

        eq_('message', ret)
        client.close()
    loop.run_until_complete(_test_call_server_side_exception())


@raises(asyncio.TimeoutError)
def test_call_socket_timeout():
    async def _test_call_socket_timeout():
        client = RPCClient(HOST, PORT, timeout=1)

        await client.call('echo_delayed', 'message', 10)
        client.close()
    loop.run_until_complete(_test_call_socket_timeout())
