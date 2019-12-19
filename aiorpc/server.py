# -*- coding: utf-8 -*-
import asyncio
import datetime

import msgpack

from aiorpc.connection import Connection
from aiorpc.constants import MSGPACKRPC_REQUEST, MSGPACKRPC_RESPONSE
from aiorpc.exceptions import MethodNotFoundError, RPCProtocolError, MethodRegisteredError
from aiorpc.log import rootLogger

__all__ = ['RPCServer', 'register', 'msgpack_init', 'set_timeout', 'serve', 'register_class']

_logger = rootLogger.getChild(__name__)
_pack_encoding = 'utf-8'
_unpack_encoding = 'utf-8'


class RPCServer:
    def __init__(self):
        self._methods = dict()
        self._class_methods = dict()
        self._pack_params = dict()
        self._unpack_params = dict(use_list=False)
        self._timeout = 3

    def register(self, name, f):
        """Register a function on the RPC server.
        Usage:
            >>> server = RPCServer()
            >>> def sum(x, y):
            >>>     return x + y
            >>> server.register('sum', sum)

        :param name: The remote name of the function, can be different with the f.__name__.
        :param f: Function object. Must be a callable object or a coroutine object.
        :return: None
        """
        if not hasattr(f, "__call__"):
            raise MethodRegisteredError("{} is not a callable object".format(f.__name__))
        if name in self._methods:
            raise MethodRegisteredError("Name {} has already been used".format(name))
        self._methods[name] = f

    def register_class(self, cls):
        """
        Registers a class on the RPC server. Methods can be accessed by ClassName.Method
        :param cls: class to load
        :return:
        """
        name = cls.__name__
        _logger.info("Loaded class `%s`", name)
        if name in self._class_methods:
            raise MethodRegisteredError("Class {} has already been loaded".format(name))
        self._class_methods[name] = cls()

    def msgpack_init(self, **kwargs):
        """Init parameters of msgpack packer and unpacker.
        Usage:
            >>> server = RPCServer()
            >>> server.msgpack_init(pack_encoding='utf-8')
        :param kwargs: See http://pythonhosted.org/msgpack-python/api.html
                default:
                pack_encoding='utf-8'
                pack_params=dict()
                unpack_encoding='utf-8'
                unpack_params=dict(use_list=False)
        :return: None
        """
        global _pack_encoding, _unpack_encoding
        _pack_encoding = kwargs.pop('pack_encoding', 'utf-8')
        _pack_params = kwargs.pop('pack_params', dict())

        _unpack_encoding = kwargs.pop('unpack_encoding', 'utf-8')
        _unpack_params = kwargs.pop('unpack_params', dict(use_list=False))

    def set_timeout(self, timeout):
        """Set the IO timeout
        Usage:
            >>> server = RPCServer()
            >>> server.set_timeout(1)

        :param timeout: Timeout. Seconds.
        :return: None
        """
        self._timeout = timeout

    async def _send_error(self, conn, exception, error, msg_id):
        response = (MSGPACKRPC_RESPONSE, msg_id, (exception, error), None)
        try:
            await conn.sendall(msgpack.packb(response, encoding=_pack_encoding, **self._pack_params),
                               self._timeout)
        except asyncio.TimeoutError as te:
            _logger.error("Timeout when _send_error %s to %s",
                          error, conn.writer.get_extra_info('peername')
                          )
        except Exception as e:
            _logger.error("Exception %s raised when _send_error %s to %s",
                          e, error, conn.writer.get_extra_info("peername")
                          )

    async def _send_result(self, conn, result, msg_id):
        _logger.debug('entering _send_result')
        response = (MSGPACKRPC_RESPONSE, msg_id, None, result)
        try:
            _logger.debug('begin to sendall')
            ret = msgpack.packb(response, encoding=_pack_encoding, **self._pack_params)
            await conn.sendall(ret, self._timeout)
            _logger.debug('sendall completed')
        except asyncio.TimeoutError as te:
            _logger.error("Timeout when _send_result %s to %s",
                          result, conn.writer.get_extra_info('peername'))
        except Exception as e:
            _logger.error("Exception %s raised when _send_result %s to %s",
                          e, result, conn.writer.get_extra_info("peername")
                          )

    def _parse_request(self, req):
        if len(req) != 4 or req[0] != MSGPACKRPC_REQUEST:
            raise RPCProtocolError('Invalid protocol')

        _, msg_id, method_name, args = req

        _method_soup = method_name.split('.')
        if len(_method_soup) == 1:
            method = self._methods.get(method_name)
        else:
            method = getattr(self._class_methods.get(_method_soup[0]), _method_soup[1])

        if not method:
            raise MethodNotFoundError("No such method {}".format(method_name))

        return msg_id, method, args, method_name

    async def serve(self, reader, writer):
        """Serve function.
        Don't use this outside asyncio.start_server.
        """
        global _unpack_encoding
        _logger.debug('enter serve: %s', writer.get_extra_info('peername'))

        conn = Connection(reader, writer,
                          msgpack.Unpacker(encoding=_unpack_encoding, **self._unpack_params))

        while not conn.is_closed():
            req = None
            try:
                req = await conn.recvall(self._timeout)
            except asyncio.TimeoutError as te:
                await asyncio.sleep(3)
                _logger.warning("Client did not send any data before timeout. Closing connection...")
                conn.close()
                continue
            except IOError as ie:
                break
            except Exception as e:
                conn.reader.set_exception(e)
                raise e

            if not isinstance(req, (tuple, list)):
                try:
                    await self._send_error(conn, "Invalid protocol", -1, None)
                    # skip the rest of iteration code after sending error
                    continue

                except Exception as e:
                    _logger.error("Error when receiving req: %s", e)

            req_start = datetime.datetime.now()
            method = None
            msg_id = None
            args = None
            try:
                _logger.debug('parsing req: %s', req)
                msg_id, method, args, method_name = self._parse_request(req)
                _logger.debug('parsing completed: %s', req)
            except Exception as e:
                _logger.error("Exception %s raised when _parse_request %s", e, req)

                # skip the rest of iteration code since we already got an error
                continue

            # Execute the parsed request
            try:
                _logger.debug('calling method: %s', method)
                ret = method.__call__(*args)
                if asyncio.iscoroutine(ret):
                    _logger.debug("start to wait_for")
                    ret = await asyncio.wait_for(ret, self._timeout)
                _logger.debug('calling %s completed. result: %s', method, ret)
            except Exception as e:
                _logger.error("Caught Exception in `%s`. %s: %s", method_name, type(e).__name__, e)
                await self._send_error(conn, type(e).__name__, str(e), msg_id)
                _logger.debug('sending exception %e completed', e)
            else:
                _logger.debug('sending result: %s', ret)
                await self._send_result(conn, ret, msg_id)
                _logger.debug('sending result %s completed', ret)

            req_end = datetime.datetime.now()
            _logger.info("Method `%s` took %fms", method_name, (req_end - req_start).microseconds / 1000)


# Backwards compatibility
_server = RPCServer()
register = _server.register
serve = _server.serve
msgpack_init = _server.msgpack_init
register_class = _server.register_class
set_timeout = _server.set_timeout
