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
# util.py
#   functions used in builtin blocks
#
import importlib
from typing import Dict, Any, List, Tuple
from dialbb.abstract_block import AbstractBlock
import re

KEY_CLASS: str = 'class'

OUTPUT_TEXT_PATTERN = re.compile(r'^(?P<utterance>.*?)\s*\((?P<kv_part>.*)\)$')
PAIR_PATTERN = re.compile(r'^\s*(?P<key>[A-Za-z0-9_]+)\s*:\s*(?P<value>.+?)\s*$')


def extract_aux_data(output_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    'sentence(key1: value1, key2: value2, key_3:value_3)'
        ↓
    ('sentence', {'key1': 'value1', 'key2': 'value2', 'key_3': 'value_3'})
    """
    output_text = output_text.strip()
    m = OUTPUT_TEXT_PATTERN.match(output_text)
    if not m:
        return output_text, {}

    utterance: str = m.group("utterance").strip()
    kv_part = m.group("kv_part")

    result_dict: Dict[str, Any] = {}
    # separate by commas
    for pair_str in kv_part.split(","):
        pair_str = pair_str.strip()
        if not pair_str:
            continue
        m2 = PAIR_PATTERN.match(pair_str)
        if not m2: # does not match pattern
            return output_text, {}

        key = m2.group("key").strip()
        value = m2.group("value").strip()
        result_dict[key] = value

    return utterance, result_dict


def create_block_object(block_config: Dict[str, Any]) -> AbstractBlock:
    """
    create a block object (tokenizer or canonicalizer)
    :param block_config: config
    :return: block object
    """

    print(f"creating block whose class is {block_config[KEY_CLASS]}.")
    block_module_name, block_class_name = block_config[KEY_CLASS].rsplit(".", 1)
    component_module = importlib.import_module(block_module_name)
    block_class = getattr(component_module, block_class_name)
    block_object = block_class(block_config, {}, "")  # create block (instance of block class)
    if not isinstance(block_object, AbstractBlock):
        raise Exception(f"{block_config[KEY_CLASS]} is not a subclass of AbstractBlock.")
    return block_object
