#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# logger.py
#   logging

__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from dialbb.util.globals import DEBUG
import logging
import sys


def get_logger(name) -> logging.Logger:
    """
    returns logger
    loggerを返す
    :param name: モジュール名
    :return: logger
    """

    # create and add handler
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s %(name)s:%(lineno)s %(funcName)s [%(levelname)s]: %(message)s'))
    logger = logging.getLogger(name)
    logger.addHandler(handler)

    # set loglevel
    if DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.propagate = False
    return logger

