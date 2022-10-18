#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# dictionary_functions.py
#   functions used in the slot sheet of the sample Japanese app

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Any, Union, List


def location() -> List[Dict[str, Union[str, List[str]]]]:
    return [{"value": "札幌", "synonyms": ["さっぽろ", "サッポロ"]},
            {"value": "荻窪", "synonyms": ["おぎくぼ"]},
            {"value": "富山"},
            {"value": "熊本"},
            {"value": "旭川"},
            {"value": "喜多方"},
            {"value": "徳島"}]








