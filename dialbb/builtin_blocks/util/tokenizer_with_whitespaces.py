#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# whitespace_tokenzer.py
#   tokenize based on whitespaces

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import re
from typing import List, Dict, Any

from dialbb.builtin_blocks.util.abstract_tokenizer import AbstractTokenizer, TokenWithIndicies


class TokenizerWithWhitespaces(AbstractTokenizer):
    """
    tokenizer based on whitespace
    Whitespaceで区切るだけのTokenizer
    """

    def __init__(self):
        super().__init__()

    def tokenize(self, input_text: str) -> List[TokenWithIndicies]:
        """
        split input text into tokens
        :param input_text: input test
        :return: list of tokens (start and end indices are dummies)
        """
        result = [TokenWithIndicies(start=-1, end=-1, form=form) for form in re.split(r'\s+', input_text)]
        return result
