#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sudachi_tokenzer.py
#   tokenize with sudachi

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from sudachipy import tokenizer
from sudachipy import dictionary
from typing import List

from dialbb.builtin_blocks.util.abstract_tokenizer import AbstractTokenizer, TokenWithIndicies


class TokenizerWithSudachi(AbstractTokenizer):
    """
    tokenizer that uses Sudachi
    Sudachiを用いたTokenizer
    """

    def __init__(self, normalize=False):
        super().__init__()
        self._tokenizer = dictionary.Dictionary().create()  # tokenizer object
        self._mode = tokenizer.Tokenizer.SplitMode.C  # sudachi tokenization mode
        self.normalize = normalize  # whether normalizing

    def tokenize(self, input_text: str) -> List[TokenWithIndicies]:
        """
        tokenizes and normalizes input with Sudachi. Normalizes  if self.normalize is True
        Sudachiを用いて単語分割（self.normalizeがTrueの時はSudachi正規化による表示ゆれ吸収も）を行う
        :param input_text: text to tokenize
        :return: list of token information
        """
        result: List[TokenWithIndicies] = []
        if self.normalize:
            result: List[TokenWithIndicies] = [TokenWithIndicies(start=m.begin(), end=m.end(), form=m.normalized_form())
                                               for m in self._tokenizer.tokenize(input_text, self._mode)]
        else:
            result = [TokenWithIndicies(start=m.begin(), end=m.end(), form=m.surface())
                      for m in self._tokenizer.tokenize(input_text, self._mode)]
        return result
