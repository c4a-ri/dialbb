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
# builtin_block_utils
#   functions used in builtin blocks
#
import importlib
from typing import Dict, Any, List
from dialbb.abstract_block import AbstractBlock

KEY_CLASS: str = 'class'


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

