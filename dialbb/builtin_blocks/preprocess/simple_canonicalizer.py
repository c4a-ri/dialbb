#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# simple_canonicalizer.py
#   canonicalize simply input string
#

import re
from dialbb.builtin_blocks.preprocess.abstract_canonicalizer import AbstractCanonicalizer


class SimpleCanonicalizer(AbstractCanonicalizer):

    def __init__(self, *args):
        super().__init__(*args)
        self._whitespace_pattern = re.compile("\s+")

    def canonicalize(self, input_text: str) -> str:
        """
        Implementation of Simple canonicalization
        :param input_text: input Japanese text
        :return: canonicalized text
        """
        result = input_text.strip()
        result = result.lower()
        result = result.replace("\n", " ")
        result = self._whitespace_pattern.sub(" ", result)
        return result
