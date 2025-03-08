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
# dialbb.py
#   main dialogue processor
#   メイン対話処理

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import copy
import dataclasses
import time
from typing import Dict, Any, List
import importlib
import yaml
import io, sys
import os
import hashlib

from dialbb.util.globals import DEBUG
from dialbb.abstract_block import AbstractBlock
from dialbb.util.error_handlers import abort_during_building
from dialbb.util.logger import get_logger


session_count = 0  # used in generating session id's
ANY_FLAG: str = "Any"
CONFIG_KEY_FLAGS_TO_USE: str = "flags_to_use"
CONFIG_KEY_LANGUAGE: str = "language"
KEY_SESSION_ID: str = 'session_id'
KEY_USER_UTTERANCE: str = 'user_utterance'
KEY_BLOCK_CLASS: str = 'block_class'
CONFIG_DIR: str = ""

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

@dataclasses.dataclass
class BlockInfo:
    """
    block object and config
    ブロックオブジェクトとconfig
    """
    block_object: AbstractBlock
    block_config: Dict[str, Any]


class DialogueProcessor:
    """
    main class of DialBB dialogue processor
    DialBB対話処理のメインクラス
    """

    config = {}

    def __init__(self, config_file: str, additional_config: Dict[str, Any] = None):
        """
        creates a DialBB application
        DialBBのアプリケーションを作成
        :param config_file: config file for the application
        :param additional_config: additional configuration
        """

        # read config file configファイルの読み込み
        print(f"reading application config file.")
        try:
            with open(config_file, encoding='utf-8') as file:
                config: Dict[str, Any] = yaml.safe_load(file)
        except Exception as e:
            raise abort_during_building(f"can't read config file: {config_file}. " + str(e))
        if additional_config:
            config.update(additional_config)

        # add directory of config file to PYTHONPATH
        # configファイルのディレクトリをPYTHONPATHに入れる
        global CONFIG_DIR
        CONFIG_DIR = os.path.dirname(config_file)
        sys.path.append(CONFIG_DIR)
        sys.path.append(os.path.join(os.path.dirname(__file__), "builtin_blocks"))

        # create dialbb dialogue processor
        # DialBBの対話処理器を作成
        print("creating dialbb dialogue processor.")
        self._blocks: List[BlockInfo] = []
        self._block_configs = config.get("blocks")
        if self._block_configs is None:
            raise Exception("no block descriptions in config.")
        for block_config in self._block_configs:
            print(f"creating block '{block_config['name']}' whose class is {block_config[KEY_BLOCK_CLASS]}.")
            block_module_name, block_class_name = block_config[KEY_BLOCK_CLASS].rsplit(".", 1)
            component_module = importlib.import_module(block_module_name)
            block_class = getattr(component_module, block_class_name)
            block_object = block_class(block_config, config, CONFIG_DIR)  # create block (instance of block class)
            if not isinstance(block_object, AbstractBlock):
                raise Exception(f"{block_config[KEY_BLOCK_CLASS]} is not a subclass of AbstractBlock.")
            block = BlockInfo(block_object=block_object, block_config=block_config)
            self._blocks.append(block)
        # todo check the formats of input of the first block and output of the last block

        self._logger = get_logger("main")

    @classmethod
    def get_config(cls):
        return cls.config

    @staticmethod
    def _generate_session_id() -> str:
        """
        create new session id string by hashing
        :return: session id string
        """

        data = str(time.time())
        hash_object = hashlib.sha256(data.encode())
        session_id = hash_object.hexdigest()
        return session_id

    def process(self, request: Dict[str, Any], initial: bool = False) -> Dict[str, Any]:
        """
        main process of DialBB application
        DialBBのメインプロセス．詳細はドキュメント参照
        :param request: request for each dialogue turn (including user utterance)
                        各ターンでのリクエスト (ユーザ発話を含む）
        :param initial: whether this is the first turn
                        最初のターンかどうか
        :return: response including system utterance
                 レスポンス　（システム発話を含む）
        """

        blackboard: Dict[str, Any] = copy.deepcopy(request)

        if initial:  # first turn
            global session_count
            session_count += 1
            # create session id string
            session_id = self._generate_session_id()
            blackboard[KEY_SESSION_ID] = session_id
            blackboard['user_utterance'] = ""
        else:
            session_id = blackboard[KEY_SESSION_ID]  # session id received from the client
        self._logger.debug(f"blackboard: " + str(blackboard))

        # each block process blackboard
        for block in self._blocks:
            input_to_block = {}
            for key_in_input, key_in_blackboard in block.block_config['input'].items():
                if key_in_blackboard not in blackboard:
                    self._logger.warning(f"key '{key_in_blackboard}' is not in the blackboard.")
                input_to_block[key_in_input] = blackboard.get(key_in_blackboard, None)
            # call each block's process method
            output_from_block = block.block_object.process(input_to_block, session_id=session_id)
            for key_in_output, key_in_blackboard in block.block_config['output'].items():
                # check if all keys are in the output
                if key_in_output not in output_from_block:
                    self._logger.error(f"key '{key_in_output}' is not in the output from the block.")
                    sys.exit(1)
                blackboard[key_in_blackboard] = output_from_block[key_in_output]
            self._logger.debug(f"blackboard: " + str(blackboard))

        # create response from the blackboard
        response = {"system_utterance": blackboard.get('system_utterance', ""),
                    "session_id": blackboard['session_id'],
                    "user_id": blackboard['user_id'],
                    "final": blackboard.get('final', False),
                    "aux_data": blackboard.get("aux_data", {})}

        return response
