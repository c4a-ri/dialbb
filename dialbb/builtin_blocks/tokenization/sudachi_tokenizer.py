#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sudachi_tokenizer.py
#   tokenize input utterance with sudachi
#   発話をSudachiで単語分割する組み込みブロック

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from typing import Dict, Any, List
from dialbb.main import CONFIG_KEY_LANGUAGE
from dialbb.util.error_handlers import abort_during_building
from dialbb.builtin_blocks.tokenization.abstract_tokenizer import TokenWithIndices, AbstractTokenizer
from sudachipy import tokenizer
from sudachipy import dictionary


# only English and Japanese are supported
# 英語、日本語のみ
supported_languages = ("en", "ja")

KEY_INPUT_TEXT = 'input_text'
KEY_TOKENS = 'tokens'
KEY_SUDACHI_NORMALIZATION = 'sudachi_normalization'


class SudachiTokenizer(AbstractTokenizer):
    """
    Block Class for tokenization
    Sudachiを用いた単語分割クラス
    """

    def __init__(self, *args):

        super().__init__(*args)
        if self.config.get(CONFIG_KEY_LANGUAGE, "ja") != 'ja':  # only for Japanese
            abort_during_building("SudachiTokenizer Block can be used for only Japanese.")

        # setting Japanese tokenizer
        self._sudachi_normalization: bool = self.block_config.get(KEY_SUDACHI_NORMALIZATION, False)
        self._tokenizer = dictionary.Dictionary().create()  # tokenizer object
        self._mode = tokenizer.Tokenizer.SplitMode.C  # sudachi tokenization mode

    def tokenize(self, input_text: str) -> List[TokenWithIndices]:
        """
        tokenizes and normalizes input with Sudachi. Normalizes  if self.sudachi_normalization is True
        Sudachiを用いて単語分割（self.sudachi_normalizationがTrueの時はSudachi正規化による表示ゆれ吸収も）を行う
        :param input_text: text to tokenize
        :return: list of tokens with indices
        """
        if input_text == "":
            result = []
        else:
            result: List[TokenWithIndices] = []
            if self._sudachi_normalization:
                result: List[TokenWithIndices] = [TokenWithIndices(start=m.begin(),
                                                                   end=m.end(),
                                                                   form=m.normalized_form())
                                                  for m in self._tokenizer.tokenize(input_text, self._mode)]
            else:
                result = [TokenWithIndices(start=m.begin(),
                                           end=m.end(),
                                           form=m.surface())
                          for m in self._tokenizer.tokenize(input_text, self._mode)]
        return result

