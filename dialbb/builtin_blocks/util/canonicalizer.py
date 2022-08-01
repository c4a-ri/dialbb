#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# canonicalizer.py
#   canonicalize input string

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import re
import zenhan

class Canonicalizer:

    def __init__(self, language:str = "en"):

        self._language = language
        self._whitespace_pattern = re.compile("\s+")

    def canonicalize(self, input_text: str) -> str:
        """
        cannlicalize text
        :param input_text: input text
        :return: canonicalized text
        """

        result = input_text
        result = result.strip()
        result = result.lower()
        if self._language == "en":
            result = result.replace("\n", " ")
            result = self._whitespace_pattern.sub(" ", result)
        elif self._language == "ja":
            result = zenhan.z2h(result, mode=3)
            result = result.replace("\n", "")
            result = self._whitespace_pattern.sub("", result)

        return result


