#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

