# -*- coding: utf-8 -*-
import asyncio
import msgpack
import logging
import functools

from aiorpc.pool import ConnectionPool
from aiorpc.log import rootLogger
from aiorpc.constants import MSGPACKRPC_RESPONSE, MSGPACKRPC_REQUEST
from aiorpc.exceptions import RPCProtocolError, RPCError

__all__ = ['RPCClient']

_logger = rootLogger.getChild(__name__)


def connection_manager(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        conn = await self._pool.acquire()
        try:
            return (await func(self, conn, *args, **kwargs))
        except Exception as exc:
            conn.reader.set_exception(exc)
            raise
        finally:
            self._pool.release(conn)

    return wrapper


class RPCClient:
    """RPC client.

    Usage:
        >>> from aiorpc.client import RPCClient
        >>> client = RPCClient('127.0.0.1', 6000)
        >>> print client.call('sum', 1, 2)
        3

    :param str host: Hostname.
    :param int port: Port number.
    :param int timeout: (optional) Socket timeout.
    :param bool lazy: (optional) If set to True, the socket connection is not
        established until you specifically call open()
    :param str pack_encoding: (optional) Character encoding used to pack data
        using Messagepack.
    :param str unpack_encoding: (optional) Character encoding used to unpack
        data using Messagepack.
    :param dict pack_params: (optional) Parameters to pass to Messagepack Packer
    :param dict unpack_params: (optional) Parameters to pass to Messagepack
    :param tcp_no_delay (optional) If set to True, use TCP_NODELAY.
    :param keep_alive (optional) If set to True, use socket keep alive.
        Unpacker
    """

    def __init__(self, host, port, timeout=3, pool_size=2, pool_minsize=None, loop=None,
                 pack_encoding='utf-8', unpack_encoding='utf-8',
                 pack_params=None, unpack_params=None):
        self._host = host
        self._port = port
        self._timeout = timeout

        if pool_minsize is None:
            self._pool = ConnectionPool(host, port, minsize=pool_size, maxsize=pool_size, loop=loop)
        else:
            self._pool = ConnectionPool(host, port, minsize=pool_minsize, maxsize=pool_size, loop=loop)

        self._msg_id = 0
        self._packer_params = pack_params or dict()
        self._unpack_encoding = unpack_encoding
        self._unpack_params = unpack_params or dict(use_list=False)

        self._packer = msgpack.Packer(encoding=pack_encoding, **self._packer_params)

    def getpeername(self):
        """Return the address of the remote endpoint."""
        return self._host, self._port

    async def close(self):
        await self._pool.clear()

    @connection_manager
    async def call(self, conn, method, *args):
        """Calls a RPC method.

        :param str method: Method name.
        :param args: Method arguments.
        """

        _logger.debug('creating request')
        req = self._create_request(method, args)

        try:
            _logger.debug('Getting connection from pool')
            conn = await asyncio.wait_for(self._pool.acquire(), self._timeout)
        except asyncio.TimeoutError as te:
            _logger.error("Get connection from pool timeout")
            raise te

        try:
            _logger.debug('Sending req: {}'.format(req))
            await conn.sendall(req, self._timeout)
            _logger.debug('Sending complete')
        except asyncio.TimeoutError as te:
            _logger.error("Write request to {}:{} timeout".format(self._host, self._port))
            raise te
        except Exception as e:
            raise e
        unpacker = msgpack.Unpacker(encoding=self._unpack_encoding,
                                    **self._unpack_params)

        data = None
        try:
            _logger.debug('receiving result from server')
            data = await conn.recvall(self._timeout)
            _logger.debug('receiving result completed')
        except asyncio.TimeoutError as te:
            _logger.error("Read request to {}:{} timeout".format(self._host, self._port))
            conn.reader.set_exception(te)
        except Exception as e:
            conn.reader.set_exception(e)
            raise e
        if data is None:
            raise IOError("Connection closed")
        unpacker.feed(data)
        response = unpacker.unpack()

        if type(response) != tuple:
            logging.debug('Protocol error, received unexpected data: {}'.format(response))
            raise RPCProtocolError('Invalid protocol')

        return self._parse_response(response)

    def _create_request(self, method, args):
        self._msg_id += 1

        req = (MSGPACKRPC_REQUEST, self._msg_id, method, args)

        return self._packer.pack(req)

    def _parse_response(self, response):
        if (len(response) != 4 or response[0] != MSGPACKRPC_RESPONSE):
            raise RPCProtocolError('Invalid protocol')

        (_, msg_id, error, result) = response

        if msg_id != self._msg_id:
            raise RPCError('Invalid Message ID')

        if error:
            raise RPCError(str(error))

        return result