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
# error_handlers.py
#   functions for handling errors
#   エラーハンドリング

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import sys, os

if os.environ.get('DIALBB_DEBUG', 'no').lower() == 'yes':
    DEBUG = True
else:
    DEBUG = False


class BuildError(BaseException):
    pass


def abort_during_building(message: str) -> None:
    """
    prints error message and aborts
    エラーメッセージを表示してアプリを終了する
    :param message: error message
    """
    if DEBUG:
        raise BuildError("Aborted during building app: " + message)
    else:
        print("Encountered an error during building app. " + message, file=sys.stdout)
    sys.exit(1)


def warn_during_building(message: str) -> None:
    """
    prints warning.
    エラーメッセージを表示する．
    :param message: warning
    """
    print("Warning during building app: " + message, file=sys.stdout)


