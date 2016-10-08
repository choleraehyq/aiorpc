# -*- coding: utf-8 -*-
import asyncio
import msgpack

from aiorpc.constants import MSGPACKRPC_REQUEST, MSGPACKRPC_RESPONSE
from aiorpc.exceptions import MethodNotFoundError, RPCProtocolError, MethodRegisteredError
from aiorpc.connection import Connection
from aiorpc.log import rootLogger

__all__ = ['register', 'msgpack_init', 'set_timeout', 'serve']

_logger = rootLogger.getChild(__name__)
_methods = dict()
_pack_encoding = 'utf-8'
_pack_params = dict()
_unpack_encoding = 'utf-8'
_unpack_params = dict(use_list=False)
_timeout = 1


def register(name, f):
    """Register a function on the RPC server.
    Usage:
        >>> def sum(x, y):
        >>>     return x + y
        >>> register('sum', sum)

    :param name: The remote name of the function, can be different with the f.__name__.
    :param f: Function object. Must be a callable object or a coroutine object.
    :return: None
    """
    global _methods
    if not hasattr(f, "__call__"):
        raise MethodRegisteredError("{} is not a callable object".format(f.__name__))
    if _methods.get(name) is not None:
        raise MethodRegisteredError("Name {} has already been used".format(name))
    _methods[name] = f


def msgpack_init(**kwargs):
    """Init parameters of msgpack packer and unpacker.
    Usage:
        >>> msgpack_init(pack_encoding='utf-8')

    :param kwargs: See http://pythonhosted.org/msgpack-python/api.html
            default:
            pack_encoding='utf-8'
            unpack_encoding='utf-8'
            unpack_params=dict(use_list=False)
    :return: None
    """
    global _pack_encoding, _pack_params, _unpack_encoding, _unpack_params
    _pack_encoding = kwargs.pop('pack_encoding', 'utf-8')
    _pack_params = kwargs.pop('pack_params', dict())

    _unpack_encoding = kwargs.pop('unpack_encoding', 'utf-8')
    _unpack_params = kwargs.pop('unpack_params', dict(use_list=False))


def set_timeout(timeout):
    """Set the IO timeout
    Usage:
        >>> set_timeout(1)

    :param timeout: Timeout. Seconds.
    :return: None
    """
    global _timeout
    _timeout = timeout

async def _send_error(conn, error, msg_id):
    global _pack_encoding, _pack_params
    response = (MSGPACKRPC_RESPONSE, msg_id, error, None)
    try:
        await conn.sendall(msgpack.packb(response, encoding=_pack_encoding, **_pack_params), _timeout)
    except asyncio.TimeoutError as te:
        _logger.error("Timeout when _send_error {} to {}".format(
            error, conn.writer.get_extra_info('peername')))
    except Exception as e:
        _logger.error("Exception {} raised when _send_error {} to {}".format(
            str(e), error, conn.writer.get_extra_info("peername")
        ))


async def _send_result(conn, result, msg_id):
    _logger.debug('entering _send_result')
    response = (MSGPACKRPC_RESPONSE, msg_id, None, result)
    try:
        _logger.debug('begin to sendall')
        ret = msgpack.packb(response, encoding=_pack_encoding, **_pack_params)
        await conn.sendall(ret, _timeout)
        _logger.debug('sendall completed')
    except asyncio.TimeoutError as te:
        _logger.error("Timeout when _send_result {} to {}".format(
            str(result), conn.writer.get_extra_info('peername')))
    except Exception as e:
        _logger.error("Exception {} raised when _send_result {} to {}".format(
            str(e), str(result), conn.writer.get_extra_info("peername")
        ))


def _parse_request(req):
    if (len(req) != 4 or req[0] != MSGPACKRPC_REQUEST):
        raise RPCProtocolError('Invalid protocol')

    (_, msg_id, method_name, args) = req

    method = _methods.get(method_name, None)

    if method is None:
        raise MethodNotFoundError("No such method {}".format(method_name))

    return (msg_id, method, args)

async def serve(reader, writer):
    """Serve function.
    Don't use this outside asyncio.start_server.
    """
    global _unpack_encoding, _unpack_params
    _logger.debug('enter serve: {}'.format(writer.get_extra_info('peername')))

    conn = Connection(reader, writer,
                      msgpack.Unpacker(encoding=_unpack_encoding, **_unpack_params))
    while not conn.is_closed():
        req = None
        try:
            req = await conn.recvall(_timeout)
        except asyncio.TimeoutError as te:
            conn.reader.set_exception(te)
        except IOError as ie:
            break
        except Exception as e:
            conn.reader.set_exception(e)
            raise e

        if type(req) != tuple:
            try:
                await _send_error(conn, "Invalid protocol", -1)
            except Exception as e:
                _logger.error("Error when receiving req: {}".format(str(e)))
                return

        method = None
        msg_id = None
        args = None
        try:
            _logger.debug('parsing req: {}'.format(str(req)))
            (msg_id, method, args) = _parse_request(req)
            _logger.debug('parsing completed: {}'.format(str(req)))
        except Exception as e:
            _logger.error("Exception {} raised when _parse_request {}".format(str(e), req))

        try:
            _logger.debug('calling method: {}'.format(str(method)))
            ret = method.__call__(*args)
            if asyncio.iscoroutine(ret):
                _logger.debug("start to wait_for")
                ret = asyncio.wait_for(ret, _timeout)
            _logger.debug('calling {} completed. result: {}'.format(str(method), str(ret)))
        except Exception as e:
            await _send_error(conn, str(e), msg_id)
        else:
            _logger.debug('sending result: {}'.format(str(ret)))
            await _send_result(conn, ret, msg_id)
            _logger.debug('sending result {} completed'.format(str(ret)))
