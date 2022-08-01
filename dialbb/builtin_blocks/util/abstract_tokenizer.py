#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# abstract_tokenzer.py
#   abstract class for tokenizer

import dataclasses
from typing import List


@dataclasses.dataclass
class Token:
    """
    token information
    """
    start: int
    end: int
    form: str


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

