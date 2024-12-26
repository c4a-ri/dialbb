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
# abstract_block.py
#   abstract building block
#   ブロックの抽象クラス
#

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Any
from typing import List

from dialbb.util.error_handlers import abort_during_building
from dialbb.util.globals import DEBUG
from dialbb.util.logger import get_logger


class AbstractBlock:
    """
    Abstract class for Building Block
    ビルディングブロックの抽象クラス
    """

    def __init__(self, *args):
        """
        initialize block with the configuration

        :param args: tuple of block config, application config, and directory of configuration file (app directory)
        """
        self.block_config, self.config, self.config_dir = args
        self.name = self.block_config.get("name", str(type(self)))  # name of this block このブロックの名前
        self._logger = get_logger(self.name)  # logger

    def process(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Processes input from the main process and outputs processed data to it.
        Input and output formats are dictionaries and the keys are defined for each concrete block.
        メインプロセスから入力を受け取り，処理結果をメインプロセスに返す．
        入出力は辞書型．キーは各具体クラス毎に決まっている。

        :param input_data: input data from the main process
        :param session_id: dialogue session id string
        :return: output data sent to the main process
        """

        raise NotImplementedError  # needs implementation

    # log functions  log関数
    # debug level
    def log_debug(self, message: str, session_id: str = "unknown") -> None:
        self._logger.debug(f"session: {session_id}, {message}")

    # info level
    def log_info(self, message: str,  session_id: str = "unknown") -> None:
        self._logger.info(f"session: {session_id}, {message}")

    # warning level
    def log_warning(self, message: str, session_id: str = "unknown") -> None:
        self._logger.warning(f"session: {session_id}, {message}")

    # error level
    def log_error(self, message: str, session_id: str = "unknown") -> None:
        self._logger.error(f"session: {session_id}, {message}")
        if DEBUG:
            raise Exception(message)

    def check_io_config(self, inputs: List[str] = None, outputs: List[str] = None,
                        optional_inputs: List[str] = None, optional_outputs: List[str] =None):
        """
        Check if input and output keys in block configuration is valid

        :param inputs: required input keys
        :param outputs: required output keys
        :param optional_inputs: optional input keys
        :param optional_outputs: optional output keys
        :return:
        """

        inputs_in_config: List[str] = self.block_config.get("input", [])
        outputs_in_config: List[str] = self.block_config.get("output", [])

        for key in inputs:
            if key not in inputs_in_config:
                abort_during_building(f"Key {key} is not in the input list of the "
                                      + f"block configuration for block {self.name}.")
        for key in outputs:
            if key not in outputs_in_config:
                abort_during_building(f"Key {key} is not in the output list of the "
                                      + f"block configuration for block {self.name}.")
        for key in inputs_in_config:
            if key not in inputs and key not in optional_inputs:
                abort_during_building(f"Key {key} in the input list of the "
                                      + f"block configuration for block {self.name} "
                                      + f"is not a required or an optional input key of the block class.")
        for key in outputs_in_config:
            if key not in outputs and key not in optional_outputs:
                abort_during_building(f"Key {key} in the output list of the "
                                      + f"block configuration for block {self.name} "
                                      + f"is not a required or an optional output key of the block class.")
















