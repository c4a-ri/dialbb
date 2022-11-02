#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# dialbb.py
#   dialbb dialogue processor

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import dataclasses
from typing import Dict, Any, List
import importlib
import yaml
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

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


@dataclasses.dataclass
class Block:
    block_object: AbstractBlock
    block_config: Dict[str, Any]


class DialogueProcessor:
    """
    main class of DialBB
    """

    config = {}

    def __init__(self, config_file: str, additional_config: Dict[str, Any] = None):
        """
        creates a DialBB application
        :param config_file: config file for the application
        :param additional_config: additional configuration
        """

        # read config file
        print(f"reading application config file.")
        try:
            with open(config_file, encoding='utf-8') as file:
                config: Dict[str, Any] = yaml.safe_load(file)
        except Exception as e:
            raise abort_during_building(f"can't read config file: {config_file}. " + str(e))
        if additional_config:
            config.update(additional_config)

        # add directory of config file to PYTHONPATH
        global CONFIG_DIR
        CONFIG_DIR = os.path.dirname(config_file)
        sys.path.append(CONFIG_DIR)
        sys.path.append(os.path.join(os.path.dirname(__file__), "builtin_blocks"))  # add to PYTHONPATH

        # create dialbb dialogue processor
        print("creating dialbb dialogue processor.")
        self._blocks: List[Block] = []
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
            block = Block(block_object=block_object, block_config=block_config)
            self._blocks.append(block)

        # todo 最初のblockのinputと最後のblockのoutputが仕様通りかをチェック

        self._logger = get_logger("main")

    @classmethod
    def get_config(cls):
        return cls.config

    def process(self, request: Dict[str, Any], initial: bool = False):

        payload: Dict[str, Any] = request

        if initial:
            global session_count
            session_count += 1
            session_id = "dialbb_session" + str(session_count)  # todo generate random session name
            payload[KEY_SESSION_ID] = session_id
            payload['user_utterance'] = ""

        self._logger.debug(f"payload: " + str(payload))
        for block in self._blocks:  # each block processes request
            input_to_block = {}
            for key_in_input, key_in_payload in block.block_config['input'].items():
                if key_in_payload not in payload:
                    self._logger.warning(f"key '{key_in_payload}' is not in the payload.")
                input_to_block[key_in_input] = payload.get(key_in_payload, None)
                input_to_block[KEY_SESSION_ID] = payload[KEY_SESSION_ID]
            output_from_block = block.block_object.process(input_to_block, initial=initial)
            for key_in_output, key_in_payload in block.block_config['output'].items():
                if key_in_output not in output_from_block:
                    self._logger.warning(f"key '{key_in_output}' is not in the output from the block.")
                payload[key_in_payload] = output_from_block[key_in_output]
            self._logger.debug(f"payload: " + str(payload))

        response = {"system_utterance": payload.get('system_utterance', ""),
                    "session_id": payload['session_id'],
                    "user_id": payload['user_id'],
                    "final": payload.get('final', False),
                    "aux_data": payload.get("aux_data", {})}

        return response
