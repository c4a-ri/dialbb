#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 C4A Research Institute, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
