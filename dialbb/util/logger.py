#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# logger.py
#   logging

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from dialbb.util.globals import DEBUG

import sys
import logging
from logging import getLogger, Formatter, StreamHandler, FileHandler
import os


def get_logger(name):

    # create and add handler
    handler = StreamHandler(stream=sys.stderr)
    handler.setFormatter(Formatter('%(asctime)s %(name)s:%(lineno)s %(funcName)s [%(levelname)s]: %(message)s'))
    logger = getLogger(name)
    logger.addHandler(handler)

    # set loglevel
    if DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.propagate = False
    return logger

