# -*- coding: utf-8 -*-
import asyncio
import logging
import msgpack

from aiorpc.connection import Connection
from aiorpc.log import rootLogger
from aiorpc.constants import MSGPACKRPC_RESPONSE, MSGPACKRPC_REQUEST
from aiorpc.exceptions import RPCProtocolError, RPCError, EnhancedRPCError

__all__ = ['RPCClient']

_logger = rootLogger.getChild(__name__)


class RPCClient:
    """RPC client.

    Usage:
        >>> from aiorpc.client import RPCClient
        >>> client = RPCClient('127.0.0.1', 6000)
        >>> import asyncio
        >>> loop = asyncio.get_event_loop()
        >>> loop.run_until_complete(client.call('sum', 1, 2))

    :param str host: Hostname.
    :param int port: Port number.
    :param int path: Unix socket path. Either this one or host and port are required.
    :param int timeout: (optional) Socket timeout.
    :param dict pack_params: (optional) Parameters to pass to Messagepack Packer
    :param dict unpack_params: (optional) Parameters to pass to Messagepack
        Unpacker.
    """

    def __init__(self, host=None, port=None, path=None, timeout=3, loop=None,
                 pack_params=None, unpack_params=None):
        self._host = host
        self._port = port
        self._path = path
        self._timeout = timeout

        self._loop = loop
        self._conn = None
        self._msg_id = 0
        self._pack_params = pack_params or dict()
        self._unpack_params = unpack_params or dict(use_list=False)

    def getpeername(self):
        """Return the address of the remote endpoint."""
        return (self._host, self._port) if self._host else ('unix', self._path)

    def close(self):
        try:
            self._conn.close()
        except AttributeError:
            pass

    async def _open_connection(self):
        _logger.debug("connect to %s:%s...", *self.getpeername())
        if self._host:
            reader, writer = await asyncio.open_connection(self._host, self._port, loop=self._loop)
        else:
            reader, writer = await asyncio.open_unix_connection(self._path, loop=self._loop)
        self._conn = Connection(reader, writer,
                                msgpack.Unpacker(raw=False,
                                                 **self._unpack_params))
        _logger.debug("Connection to %s:%s established", *self.getpeername())

    async def call(self, method, *args, _close=False):
        """Calls a RPC method.

        :param str method: Method name.
        :param args: Method arguments.
        :param _close: Close the connection at the end of the request. Defaults to false
        """

        _logger.debug('creating request')
        req = self._create_request(method, args)

        if self._conn is None or self._conn.is_closed():
            await self._open_connection()

        try:
            _logger.debug('Sending req: %s', req)
            await self._conn.sendall(req, self._timeout)
            _logger.debug('Sending complete')
        except asyncio.TimeoutError as te:
            _logger.error("Write request to %s:%s timeout", *self.getpeername())
            raise te
        except Exception as e:
            raise e

        response = None
        try:
            _logger.debug('receiving result from server')
            response = await self._conn.recvall(self._timeout)
            _logger.debug('receiving result completed')
        except asyncio.TimeoutError as te:
            _logger.error("Read request to %s:%s timeout", *self.getpeername())
            self._conn.reader.set_exception(te)
            raise te
        except Exception as e:
            self._conn.reader.set_exception(e)
            raise e

        if response is None:
            raise IOError("Connection closed")

        if not isinstance(response, tuple):
            logging.debug('Protocol error, received unexpected data: %r', response)
            raise RPCProtocolError('Invalid protocol')

        if _close:
            self.close()

        return self._parse_response(response)

    async def call_once(self, method, *args):
        """Call an RPC Method, then close the connection

        :param str method: Method name.
        :param args: Method arguments.
        :param _close: Close the connection at the end of the request. Defaults to false
        """
        return await self.call(method, *args, _close=True)

    def _create_request(self, method, args):
        self._msg_id += 1

        req = (MSGPACKRPC_REQUEST, self._msg_id, method, args)

        return msgpack.packb(req, **self._pack_params)

    def _parse_response(self, response):
        if (len(response) != 4 or response[0] != MSGPACKRPC_RESPONSE):
            raise RPCProtocolError('Invalid protocol')

        (_, msg_id, error, result) = response

        if msg_id != self._msg_id:
            raise RPCError('Invalid Message ID')

        if error and len(error) == 2:
            raise EnhancedRPCError(*error)
        elif error:
            raise RPCError(error)

        return result

    async def __aenter__(self):
        await self._open_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn and not self._conn.is_closed():
            logging.debug('Closing connection from context manager')
            self.close()
