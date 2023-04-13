#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# abstract_canonicalizer.py
#   abstract class for canonicalization block
#   発話文字列正規化の組み込みブロックの抽象クラス

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from dialbb.abstract_block import AbstractBlock
from dialbb.main import CONFIG_KEY_LANGUAGE, KEY_SESSION_ID
from typing import Any, Dict

KEY_INPUT_TEXT: str = "input_text"  # key in input_data
KEY_OUTPUT_TEXT: str = "output_text" # key in output data


class AbstractCanonicalizer(AbstractBlock):
    """
    Abstract Class for Canonicalizer Block
    正規化ブロックの抽象クラス
    """

    def __init__(self, *args):
        super().__init__(*args)

    def process(self, input_data: Dict[str, Any], session_id: str = "undecided") -> Dict[str, Any]:
        """
        canonicalizes input text
        入力文字列を正規化
        :param input_data: {'input_text': <input text: str>}
        :param session_id: the id of the dialogue session
        :return: output data. {"output_text': <canonicalized text: str>}
        """
        session_id = input_data.get(KEY_SESSION_ID, "undecided")  # for logging
        self.log_debug("input: " + str(input_data), session_id=session_id)
        input_text: str = input_data[KEY_INPUT_TEXT]
        if input_text == "":
            result = ""
        else:
            result = self.canonicalize(input_text)
        output = {KEY_OUTPUT_TEXT: result}
        self.log_debug("output: " + str(output), session_id=session_id)
        return output

    def canonicalize(self, input_text: str) -> str:
        """
        Function to canonicalize input text. To be implemented.
        :type input_text: input text
        :return: canonicalized text
        """
        raise NotImplementedError


