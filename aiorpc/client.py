# -*- coding: utf-8 -*-
import asyncio
import msgpack
import logging

from aiorpc.connection import Connection
from aiorpc.log import rootLogger
from aiorpc.constants import MSGPACKRPC_RESPONSE, MSGPACKRPC_REQUEST
from aiorpc.exceptions import RPCProtocolError, RPCError

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
    :param int timeout: (optional) Socket timeout.
    :param str pack_encoding: (optional) Character encoding used to pack data
        using Messagepack.
    :param str unpack_encoding: (optional) Character encoding used to unpack
        data using Messagepack.
    :param dict pack_params: (optional) Parameters to pass to Messagepack Packer
    :param dict unpack_params: (optional) Parameters to pass to Messagepack
        Unpacker.
    """

    def __init__(self, host, port, *, timeout=3, loop=None,
                 pack_encoding='utf-8', unpack_encoding='utf-8',
                 pack_params=None, unpack_params=None):
        self._host = host
        self._port = port
        self._timeout = timeout

        self._loop = loop
        self._conn = None
        self._msg_id = 0
        self._pack_encoding = pack_encoding
        self._pack_params = pack_params or dict()
        self._unpack_encoding = unpack_encoding
        self._unpack_params = unpack_params or dict(use_list=False)

    def getpeername(self):
        """Return the address of the remote endpoint."""
        return self._host, self._port

    def close(self):
        self._conn.close()

    async def call(self, method, *args):
        """Calls a RPC method.

        :param str method: Method name.
        :param args: Method arguments.
        """

        _logger.debug('creating request')
        req = self._create_request(method, args)

        if self._conn is None:
            _logger.debug("connect to {}:{}...".format(self._host, self._port))
            reader, writer = await asyncio.open_connection(self._host, self._port, loop=self._loop)
            self._conn = Connection(reader, writer,
                                    msgpack.Unpacker(encoding=self._unpack_encoding, **self._unpack_params))
            _logger.debug("Connection to {}:{} established".format(self._host, self._port))

        try:
            _logger.debug('Sending req: {}'.format(req))
            await self._conn.sendall(req, self._timeout)
            _logger.debug('Sending complete')
        except asyncio.TimeoutError as te:
            _logger.error("Write request to {}:{} timeout".format(self._host, self._port))
            raise te
        except Exception as e:
            raise e

        response = None
        try:
            _logger.debug('receiving result from server')
            response = await self._conn.recvall(self._timeout)
            _logger.debug('receiving result completed')
        except asyncio.TimeoutError as te:
            _logger.error("Read request to {}:{} timeout".format(self._host, self._port))
            self._conn.reader.set_exception(te)
            raise te
        except Exception as e:
            self._conn.reader.set_exception(e)
            raise e

        if response is None:
            raise IOError("Connection closed")

        if type(response) != tuple:
            logging.debug('Protocol error, received unexpected data: {}'.format(response))
            raise RPCProtocolError('Invalid protocol')

        return self._parse_response(response)

    def _create_request(self, method, args):
        self._msg_id += 1

        req = (MSGPACKRPC_REQUEST, self._msg_id, method, args)

        return msgpack.packb(req, encoding=self._pack_encoding, **self._pack_params)

    def _parse_response(self, response):
        if (len(response) != 4 or response[0] != MSGPACKRPC_RESPONSE):
            raise RPCProtocolError('Invalid protocol')

        (_, msg_id, error, result) = response

        if msg_id != self._msg_id:
            raise RPCError('Invalid Message ID')

        if error:
            raise RPCError(str(error))

        return result
