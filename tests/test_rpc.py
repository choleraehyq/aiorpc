# -*- coding: utf-8 -*-


import asyncio

from nose.tools import *
import uvloop

from aiorpc import RPCClient, register, serve, register_class
from aiorpc.exceptions import RPCError, EnhancedRPCError

HOST = 'localhost'
PORT = 6000
PATH = './test.socket'
loop = None
inet_server = None
unix_server = None


def setup_module():
    print("setup")
    set_up_inet_server()
    set_up_unix_server()
    register_handlers()


def teardown_module():
    print("teardown")
    inet_server.close()
    unix_server.close()
    loop.stop()
    #loop.run_until_complete(inet_server.wait_closed())


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


def set_up_inet_server():
    global loop, inet_server
    if not loop:
        loop = uvloop.new_event_loop()
        asyncio.set_event_loop(loop)
    coro = asyncio.start_server(serve, HOST, PORT)
    inet_server = loop.run_until_complete(coro)

def set_up_unix_server():
    global loop, unix_server
    if not loop:
        loop = uvloop.new_event_loop()
        asyncio.set_event_loop(loop)
    coro = asyncio.start_unix_server(serve, PATH)
    unix_server = loop.run_until_complete(coro)

def register_handlers():
    register('echo', echo)
    register('echo_delayed', echo_delayed)
    register('raise_error', raise_error)
    register_class(my_class)


# Test basic RPC Call
def test_inet_call():
    async def _test_call():
        client = RPCClient(HOST, PORT)
        ret = await client.call('echo', 'message')

        eq_('message', ret)
        client.close()

    loop.run_until_complete(_test_call())

def test_unix_call():
    async def _test_call():
        client = RPCClient(path=PATH)
        ret = await client.call('echo', 'message')

        eq_('message', ret)
        client.close()

    loop.run_until_complete(_test_call())


def test_inet_context_manager():
    async def _test_context_manager():
        async with RPCClient(HOST, PORT) as client:
            ret = await client.call('echo', 'message')
            eq_('message', ret)

    loop.run_until_complete(_test_context_manager())

def test_unix_context_manager():
    async def _test_context_manager():
        async with RPCClient(path=PATH) as client:
            ret = await client.call('echo', 'message')
            eq_('message', ret)

    loop.run_until_complete(_test_context_manager())


@raises(RPCError)
def test_call_inet_server_side_exception():
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

@raises(RPCError)
def test_call_unxi_server_side_exception():
    async def _test_call_server_side_exception():
        client = RPCClient(path=PATH)

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
def test_call_inet_socket_timeout():
    async def _test_call_socket_timeout():
        client = RPCClient(HOST, PORT, timeout=1)

        await client.call('echo_delayed', 'message', 10)
        client.close()
    loop.run_until_complete(_test_call_socket_timeout())

@raises(asyncio.TimeoutError)
def test_call_unix_socket_timeout():
    async def _test_call_socket_timeout():
        client = RPCClient(path=PATH, timeout=1)

        await client.call('echo_delayed', 'message', 10)
        client.close()
    loop.run_until_complete(_test_call_socket_timeout())


# Test call once
def test_inet_call_once():
    async def _test_call():
        client = RPCClient(HOST, PORT)
        ret = await client.call_once('echo', 'message')

        eq_('message', ret)
        eq_(client._conn.is_closed(), True)

        # Make sure we can make another call after we do a call_once
        ret = await client.call_once('echo', 'message again')

        eq_('message again', ret)

    loop.run_until_complete(_test_call())

def test_unix_call_once():
    async def _test_call():
        client = RPCClient(path=PATH)
        ret = await client.call_once('echo', 'message')

        eq_('message', ret)
        eq_(client._conn.is_closed(), True)

        # Make sure we can make another call after we do a call_once
        ret = await client.call_once('echo', 'message again')

        eq_('message again', ret)

    loop.run_until_complete(_test_call())


# Test class method
def test_inet_class_call():
    async def _test_class_call():
        client = RPCClient(HOST, PORT)
        ret = await client.call('my_class.echo', 'message')

        eq_('message', ret)
        client.close()

    loop.run_until_complete(_test_class_call())

def test_unix_class_call():
    async def _test_class_call():
        client = RPCClient(path=PATH)
        ret = await client.call('my_class.echo', 'message')

        eq_('message', ret)
        client.close()

    loop.run_until_complete(_test_class_call())