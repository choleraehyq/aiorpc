# -*- coding: utf-8 -*-

import asyncio
import platform
import socket
from aiorpc.log import rootLogger
from aiorpc.constants import SOCKET_RECV_SIZE


__all__ = ['Connection']
_logger = rootLogger.getChild(__name__)


def set_keepalive(sock, after_idle_sec=1, interval_sec=3, max_fails=5):
    """Set TCP keepalive on an open socket.

    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 seconds
    """
    if platform.system() == 'Linux':
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        #  sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
        #  sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
        #  sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)
        #  sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, after_idle_sec * 1000, interval_sec * 10000))
    elif platform.system() == 'Darwin':
        TCP_KEEPALIVE = 0x10
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, interval_sec)
    elif platform.system() == 'Windows':
        sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, after_idle_sec * 1000, interval_sec * 10000))


class Connection:
    def __init__(self, reader, writer, unpacker):
        self.reader = reader
        self.writer = writer
        self.unpacker = unpacker
        self._is_closed = False
        self.peer = self.writer.get_extra_info('peername')

        if hasattr(socket, 'SO_KEEPALIVE'):
            sock = self.writer.get_extra_info('socket')
            set_keepalive(sock)

    async def sendall(self, raw_req, timeout):
        _logger.debug('sending raw_req %s to %s', raw_req, self.peer)
        self.writer.write(raw_req)
        await asyncio.wait_for(self.writer.drain(), timeout)
        _logger.debug('sending %s completed', raw_req)

    async def recvall(self, timeout):
        _logger.debug('entered recvall from %s', self.peer)
        # buffer, line = bytearray(), b''
        # while not line.endswith(b'\r\n'):
        #     _logger.debug('receiving data, timeout: {}'.format(timeout))
        #     line = await asyncio.wait_for(self.reader.readline(), timeout)
        #     if not line:
        #         break
        #     _logger.debug('received data {}'.format(line))
        #     buffer.extend(line)
        # _logger.debug('buffer: {}'.format(buffer))
        reqs = []
        while True:
            data = await asyncio.wait_for(self.reader.read(SOCKET_RECV_SIZE), timeout)
            _logger.debug('receiving data %s from %s', data, self.peer)
            if not data:
                raise IOError('Connection to {} closed'.format(self.peer))
            self.unpacker.feed(data)
            reqs = [*self.unpacker]
            if len(reqs) == 0:
                continue
            break
        _logger.debug('received reqs from %s : %s', self.peer, reqs)
        _logger.debug('exiting recvall from %s', self.peer)
        return reqs

    def close(self):
        self.reader.feed_eof()
        self.writer.close()
        self._is_closed = True

    def is_closed(self):
        return self._is_closed
