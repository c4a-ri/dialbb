#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# abstract_block.py
#   abstract building block
#   ブロックの抽象クラス
#

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Any
from dialbb.util.logger import get_logger


class AbstractBlock:
    """
    Abstract class for Building Block
    ビルディングブロックの抽象クラス
    """

    def __init__(self, *args):

        # block config, application config, and directory of configuration file (app directory)
        self.block_config, self.config, self.config_dir = args
        self.name = self.block_config.get("name", None)  # name of this block このブロックの名前
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












