#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# utterance_canonicalizer.py
#   canonicalization block
#   発話文字列正規化の組み込みブロック

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from dialbb.builtin_blocks.util.canonicalizer import Canonicalizer
from dialbb.abstract_block import AbstractBlock
from dialbb.main import CONFIG_KEY_LANGUAGE, KEY_SESSION_ID
from typing import Any, Dict

KEY_INPUT_TEXT: str = "input_text"  # key in input_data
KEY_OUTPUT_TEXT: str = "output_text" # key in output data

# only English and Japanese are supported
# 英語、日本語のみ
supported_languages = ("en", "ja")


class UtteranceCanonicalizer(AbstractBlock):
    """
    Block Class for canonicalizer
    正規化クラス
    """

    def __init__(self, *args):

        super().__init__(*args)
        # default language is Japanese デフォルト言語は日本語
        self._language = self.config.get(CONFIG_KEY_LANGUAGE, "ja")  # language 言語
        # check if language is supported 言語がサポートされているかどうかをチェック
        if self._language not in supported_languages:
            self.log_error(f"{self._language} is not a supported language. Supported languages are: "
                           + str(supported_languages))
        self._canonicalizer = Canonicalizer(self._language)  # canonicalizer

    def process(self, input_data: Dict[str, Any], session_id: str = "undecided") -> Dict[str, Any]:
        """
        canonicalizes input text
        入力文字列を正規化
        :param input_data: {'input_text': <input text: str>}
        :param session_id: the id of the dialogue session
        :return: output data. {"output_text': <canonicalized text: str>}
        """

        session_id = input_data.get(KEY_SESSION_ID, "undecided") # for logging
        self.log_debug("input: " + str(input_data), session_id=session_id)
        input_text: str = input_data[KEY_INPUT_TEXT]
        if input_text == "":
            result = ""
        else:
            result = self._canonicalizer.canonicalize(input_text)
        output = {KEY_OUTPUT_TEXT: result}
        self.log_debug("output: " + str(output), session_id=session_id)
        return output
