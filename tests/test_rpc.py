# -*- coding: utf-8 -*-


import asyncio

from nose.tools import *
import uvloop

from aiorpc import RPCClient, register, serve, register_class
from aiorpc.exceptions import RPCError, EnhancedRPCError

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
    loop.stop()
    #loop.run_until_complete(server.wait_closed())


class my_class:
    def echo(self, msg):
        return msg


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
    register_class(my_class)
    coro = asyncio.start_server(serve, HOST, PORT)
    server = loop.run_until_complete(coro)

# Test basic RPC Call
def test_call():
    async def _test_call():
        client = RPCClient(HOST, PORT)
        ret = await client.call('echo', 'message')

        eq_('message', ret)
        client.close()

    loop.run_until_complete(_test_call())

    
def test_context_manager():
    async def _test_context_manager():
        async with RPCClient(HOST, PORT) as client:
            ret = await client.call('echo', 'message')
            eq_('message', ret)
    loop.run_until_complete(_test_context_manager())

    
@raises(RPCError)
def test_call_server_side_exception():
    async def _test_call_server_side_exception():
        client = RPCClient(HOST, PORT)

        try:
            ret = await client.call('raise_error')
        except EnhancedRPCError as e:
            client.close()
            eq_(e.parent, 'Exception')
            eq_('error msg', e.message)
            eq_('Exception: error msg', str(e))
            raise RPCError

        eq_('message', ret)
    loop.run_until_complete(_test_call_server_side_exception())


# Test socket timeouts
@raises(asyncio.TimeoutError)
def test_call_socket_timeout():
    async def _test_call_socket_timeout():
        client = RPCClient(HOST, PORT, timeout=1)

        await client.call('echo_delayed', 'message', 10)
        client.close()
    loop.run_until_complete(_test_call_socket_timeout())


# Test call once
def test_call_once():
    async def _test_call():
        client = RPCClient(HOST, PORT)
        ret = await client.call_once('echo', 'message')

        eq_('message', ret)
        eq_(client._conn.is_closed(), True)

        # Make sure we can make another call after we do a call_once
        ret = await client.call_once('echo', 'message again')

        eq_('message again', ret)

    loop.run_until_complete(_test_call())


# Test class method
def test_class_call():
    async def _test_class_call():
        client = RPCClient(HOST, PORT)
        ret = await client.call('my_class.echo', 'message')

        eq_('message', ret)
        client.close()

    loop.run_until_complete(_test_class_call())
