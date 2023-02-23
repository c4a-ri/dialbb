#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sudachi_tokenizer.py
#   tokenize input utterance
#   発話を単語分割する組み込みブロック

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from typing import Dict, Any, List
from dialbb.abstract_block import AbstractBlock
from dialbb.main import CONFIG_KEY_LANGUAGE, KEY_SESSION_ID
from dialbb.builtin_blocks.util.tokenizer_with_sudachi import TokenizerWithSudachi
from dialbb.util.error_handlers import abort_during_building

# only English and Japanese are supported
# 英語、日本語のみ
supported_languages = ("en", "ja")

KEY_INPUT_TEXT = 'input_text'
KEY_TOKENS = 'tokens'
KEY_SUDACHI_NORMALIZATION = 'sudachi_normalization'


class SudachiTokenizer(AbstractBlock):
    """
    Block Class for tokenization
    Sudachiを用いた単語分割クラス
    """

    def __init__(self, *args):

        super().__init__(*args)
        if self.config.get(CONFIG_KEY_LANGUAGE, "ja") != 'ja':  # only for Japanese
            abort_during_building("SudachiTokenizer Block can be used for only Japanese.")

        # setting Japanese tokenizer

        sudachi_normalization: bool = self.block_config.get(KEY_SUDACHI_NORMALIZATION, False)
        self._tokenizer = TokenizerWithSudachi(normalize=sudachi_normalization)

    def process(self, input_data: Dict[str, Any], session_id: str = "undecided") -> Dict[str, List[str]]:
        """
        tokenize input text
        入力文字列を正規化
        :param input_data: {'input_text': <input text: str>}
        :param session_id: the id of the dialogue session
        :return: output data. {"output_text': tokens: str>}
        """

        session_id = input_data.get(KEY_SESSION_ID, "undecided") # for logging
        self.log_debug("input: " + str(input_data), session_id=session_id)
        input_text: str = input_data[KEY_INPUT_TEXT]
        if input_text == "":
            result = ""
        else:
            result = self._tokenizer.tokenize(input_text)
        output = {KEY_TOKENS: result}
        self.log_debug("output: " + str(output), session_id=session_id)
        return output
