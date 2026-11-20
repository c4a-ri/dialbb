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


import logging
import os
import sys


_MANAGED_LOGGERS: set[str] = set()


def _is_debug_enabled() -> bool:
    return os.environ.get("DIALBB_DEBUG", "no").lower() in ("yes", "true")


def _get_logging_config() -> tuple[int, str]:
    if _is_debug_enabled():
        return logging.DEBUG, '%(funcName)s: %(message)s'
    return (
        logging.INFO,
        '%(asctime)s %(name)s:%(lineno)s %(funcName)s [%(levelname)s]: %(message)s',
    )


def _configure_logger(logger: logging.Logger) -> logging.Logger:
    level, format_string = _get_logging_config()
    logger.setLevel(level)

    formatter = logging.Formatter(format_string)
    stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    if not stream_handlers:
        stream_handlers = [logging.StreamHandler(sys.stdout)]
        logger.addHandler(stream_handlers[0])

    for handler in stream_handlers:
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        handler.stream = sys.stdout

    logger.propagate = False
    return logger


def configure_dialbb_logging() -> None:
    for logger_name in _MANAGED_LOGGERS:
        logger = logging.getLogger(logger_name)
        _configure_logger(logger)


def get_logger(name) -> logging.Logger:
    """
    returns logger
    loggerを返す
    :param name: モジュール名
    :return: logger
    """

    logger = logging.getLogger(name)
    _MANAGED_LOGGERS.add(name)
    return _configure_logger(logger)

