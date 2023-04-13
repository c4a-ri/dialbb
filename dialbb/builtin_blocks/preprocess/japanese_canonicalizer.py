#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# japanese_canonicalizer.py
#   日本語用発話文字列正規化ブロック
#

import jaconv
import re
from dialbb.builtin_blocks.preprocess.abstract_canonicalizer import AbstractCanonicalizer
from dialbb.util.error_handlers import abort_during_building

CONFIG_KEY_LANGUAGE: str = "language"

class JapaneseCanonicalizer(AbstractCanonicalizer):

    def __init__(self, *args):
        super().__init__(*args)
        if self.config.get(CONFIG_KEY_LANGUAGE, "ja") != 'ja':  # only for Japanese
            abort_during_building("JapaneseCanonicalizer Block can be used for only Japanese.")
        self._whitespace_pattern = re.compile("\s+")


    def canonicalize(self, input_text: str) -> str:
        """
        Implementation of Japanese canonicalization
        :param input_text: input Japanese text
        :return: canonicalized text
        """
        result = input_text.strip()
        result = result.lower()
        result = jaconv.z2h(result, kana=False, ascii=True, digit=True)
        result = jaconv.normalize(result, 'NFKC')
        result = result.replace("\n", "")
        result = self._whitespace_pattern.sub(" ", result)
        return result
