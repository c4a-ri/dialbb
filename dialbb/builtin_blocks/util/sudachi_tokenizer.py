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

from dialbb.builtin_blocks.util.abstract_tokenizer import AbstractTokenizer, Token


class SudachiTokenizer(AbstractTokenizer):
    """
    tokenizer that uses Sudachi
    """

    def __init__(self, normalize=False):
        super().__init__()
        self._tokenizer = dictionary.Dictionary().create()
        self._mode = tokenizer.Tokenizer.SplitMode.C
        self.normalize = normalize

    def tokenize(self, input_text: str) -> List[Token]:
        """
        tokenize input with Sudachi
        :param input_text: text to tokenize
        :return: list of token information
        """
        result: List[Token] = []
        if self.normalize:
            result: List[Token] = [Token(start=m.begin(), end=m.end(), form=m.normalized_form())
                                   for m in self._tokenizer.tokenize(input_text, self._mode)]
        else:
            result = [Token(start=m.begin(), end=m.end(), form=m.surface())
                      for m in self._tokenizer.tokenize(input_text, self._mode)]
        return result
