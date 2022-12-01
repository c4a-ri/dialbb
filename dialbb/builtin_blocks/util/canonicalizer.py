#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# canonicalizer.py
#   canonicalize input string

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import re
import jaconv

class Canonicalizer:
    """
    canonicalizer class
    正規化クラス
    """

    def __init__(self, language:str = "ja"):

        self._language = language  # language ('ja' or 'en')
        self._whitespace_pattern = re.compile("\s+")

    def canonicalize(self, input_text: str) -> str:
        """
        cannlicalizes text. lowercases, converts to hankaku, and perform unicode
        入力文字列の正規化を行う。日本語の場合
        :param input_text: input text string
        :return: canonicalized text
        """

        result = input_text
        result = result.strip()
        result = result.lower()
        if self._language == "en":
            result = result.replace("\n", " ")
            result = self._whitespace_pattern.sub(" ", result)
        elif self._language == "ja":
            result = jaconv.z2h(result, kana=False, ascii=True, digit=True)
            result = jaconv.normalize(result, 'NFKC')
            result = result.replace("\n", "")
            result = self._whitespace_pattern.sub("", result)

        return result


