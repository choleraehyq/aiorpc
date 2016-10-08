aiorpc
======

.. image:: https://badge.fury.io/py/aiorpc.png
    :target: http://badge.fury.io/py/aiorpc

.. image:: https://travis-ci.org/choleraehyq/aiorpc.png?branch=master
    :target: https://travis-ci.org/choleraehyq/aiorpc

aiorpc is a lightweight asynchronous RPC library. It enables you to easily build a distributed server-side system by writing a small amount of code. It is built on top of `asyncio <https://docs.python.org/3/library/asyncio.html/>`_ and `MessagePack <http://msgpack.org/>`_.


Installation
------------

To install aiorpc, simply:

.. code-block:: bash

    $ pip install aiorpc

Examples
--------

RPC server
^^^^^^^^^^

.. code-block:: python

    from aiorpc import register, serve

    import asyncio
    import uvloop


    def echo(msg):
        return msg

    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    register("echo", echo)
    coro = asyncio.start_server(serve, '127.0.0.1', 6000, loop=loop)
    server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        server.close()
        loop.run_until_complete(server.wait_closed())

RPC client
^^^^^^^^^^

.. code-block:: python

    from aiorpc import RPCClient

    import asyncio
    import uvloop

    async def do(cli):
        ret = await client.call('echo', 'message')
        print("{}\n".format(ret))

    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    client = RPCClient('127.0.0.1', 6000)
    loop.run_until_complete(do(client))
    client.close()

Performance
-----------

aiorpc with `uvloop <https://github.com/MagicStack/uvloop>`_ significantly outperforms `ZeroRPC <http://zerorpc.dotcloud.com/>`_ (**6x** faster), which is built using `ZeroMQ <http://zeromq.org/>`_ and `MessagePack <http://msgpack.org/>`_ and slightly underperforms `official MessagePack RPC <https://github.com/msgpack-rpc/msgpack-rpc-python>`_ (**0.7x** slower), which is built using `Facebook's Tornado <http://www.tornadoweb.org/en/stable/>`_ and `MessagePack <http://msgpack.org/>`_.

- aiorpc


.. code-block:: bash

    % python benchmarks/benchmark_aiorpc.py
    call: 2236 qps


- Official MesssagePack RPC

.. code-block:: bash

    % pip install msgpack-rpc-python
    % python benchmarks/benchmark_msgpackrpc.py
    call: 3112 qps

- ZeroRPC

.. code-block:: bash

    % pip install zerorpc
    % python benchmarks/benchmark_zerorpc.py
    call: 351 qps


Documentation
-------------

Documentation is available at http://aiorpc.readthedocs.org/.
(Since readthedocs don't support Python 3.5 yet, this page is unavailable now.)
