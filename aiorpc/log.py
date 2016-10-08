# -*- coding: utf-8 -*-
import logging

rootLogger = logging.getLogger('aiorpc')
_handler = logging.StreamHandler()
_formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
_handler.setFormatter(_formatter)
rootLogger.addHandler(_handler)
rootLogger.setLevel(logging.ERROR)
