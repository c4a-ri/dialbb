#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# abstract_tokenzer.py
#   abstract class for tokenizer
#   単語分割の抽象クラス

import dataclasses
from typing import List


@dataclasses.dataclass
class Token:
    """
    token information
    トークン情報
    """
    start: int  # start index in the string  (from <start>-th character)
    end: int  # end index in the string (to <end>-th character)
    form: str  # token string


class AbstractTokenizer:

    def __init__(self):
        pass

    def tokenize(self, input_text: str) -> List[Token]:
        """
        tokzenize input into list of Token objects
        :param input_text: input text
        :return: list of Token object
        """

        raise NotImplementedError

