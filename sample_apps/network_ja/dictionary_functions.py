#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# dictionary_functions.py
#   functions used as dictionary in the sample Japanese app
#   日本語サンプルアプリで辞書代わりに使われる関数

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Union, List, Any


def location(config: Dict[str, Any], block_config: Dict[str, Any]) -> List[Dict[str, Union[str, List[str]]]]:
    """
    locationの辞書項目を返す．この例ではあらかじめ用意した辞書情報を返しているが，
    外部DBにアクセスして辞書情報をとってくるような用途で用いられる
    :param config: application config （未使用）
    :param block_config: block config （未使用）
    :return: 辞書情報
    """
    return [{"entity": "札幌", "synonyms": ["さっぽろ", "サッポロ"]},
            {"entity": "荻窪", "synonyms": ["おぎくぼ"]},
            {"entity": "富山"},
            {"entity": "熊本"},
            {"entity": "旭川"},
            {"entity": "喜多方"},
            {"entity": "徳島"}]








