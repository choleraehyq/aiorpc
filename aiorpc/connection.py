# -*- coding: utf-8 -*-

import asyncio
from aiorpc.log import rootLogger
from aiorpc.constants import SOCKET_RECV_SIZE

__all__ = ['Connection']
_logger = rootLogger.getChild(__name__)


class Connection:
    def __init__(self, reader, writer, unpacker):
        self.reader = reader
        self.writer = writer
        self.unpacker = unpacker
        self._is_closed = False
        self.peer = self.writer.get_extra_info('peername')

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
        req = None
        while True:
            data = await asyncio.wait_for(self.reader.read(SOCKET_RECV_SIZE), timeout)
            _logger.debug('receiving data %s from %s', data, self.peer)
            if not data:
                raise IOError('Connection to {} closed'.format(self.peer))
            self.unpacker.feed(data)
            try:
                req = next(self.unpacker)
                break
            except StopIteration:
                continue
        _logger.debug('received req from %s : %s', self.peer, req)
        _logger.debug('exiting recvall from %s', self.peer)
        return req

    def close(self):
        self.reader.feed_eof()
        self.writer.close()
        self._is_closed = True

    def is_closed(self):
        return self._is_closed
