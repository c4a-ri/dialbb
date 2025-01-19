#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 C4A Research Institute, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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

