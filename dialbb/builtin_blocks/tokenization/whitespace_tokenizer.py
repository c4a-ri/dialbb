#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# whitespace_tokenizer.py
#   tokenize input utterance with whitespaces

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from typing import Dict, Any, List
from dialbb.builtin_blocks.tokenization.abstract_tokenizer import TokenWithIndices, AbstractTokenizer


KEY_INPUT_TEXT = 'input_text'
KEY_TOKENS = 'tokens'


class WhitespaceTokenizer(AbstractTokenizer):
    """
    Block Class for tokenization
    """

    def __init__(self, *args):

        super().__init__(*args)

    def tokenize(self, input_text: str) -> List[TokenWithIndices]:

        """
        split input text into tokens
        :param input_text: input test (assumed to have been canonicalized with SimpleCanonicalizer)
        :return: list of tokens
        """

        if input_text == "":
            return []

        if input_text[0] == ' ':
            self.log_warning("input is not canonicalized: " + input_text)
            return []

        result: List[TokenWithIndices] = []
        start = 0
        form = ""
        for index, char in enumerate(input_text):
            if char == ' ':
                result.append(TokenWithIndices(start=start, end=index, form=form))
                start = index + 1
            else:
                form += char
        return result

