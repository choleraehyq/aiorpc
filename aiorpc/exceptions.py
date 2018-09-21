# -*- coding: utf-8 -*-


class RPCProtocolError(Exception):
    pass


class MethodNotFoundError(Exception):
    pass


class RPCError(Exception):
    pass


class EnhancedRPCError(Exception):
    def __init__(self, parent, message):
        self.parent = parent
        self.message = message

        Exception.__init__(self, "{0}: {1}".format(parent, message))


class MethodRegisteredError(Exception):
    pass
