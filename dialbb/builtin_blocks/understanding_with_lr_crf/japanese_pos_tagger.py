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
# japanese_pos_tagger.py
#   tokenize input utterance with sudachi for LR-CRF understander
#   発話をSudachiで単語分割する組み込みブロック

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from typing import Dict, Any, List, Tuple

class JapanesePosTagger:

    """
    Japanese Tokenizer
    """

    def __init__(self):

        from sudachipy import tokenizer
        from sudachipy import dictionary

        # setting Japanese tokenizer
        self._tokenizer = dictionary.Dictionary().create()  # tokenizer object
        self._mode = tokenizer.Tokenizer.SplitMode.C  # sudachi tokenization mode

    def tag(self, input_text: str) -> List[Tuple[str, str]]:

        """
        tokenizes input with Sudachi and tags POS labels
        Sudachiを用いて単語分割し、POS tagをつける
        :param input_text: text to tokenize
        :return: list of Tuples of tokens and pos e.g., [(word, pos), (word, pos) ...]
        """
        if input_text == "":
            result = []
        else:
            result = [(m.surface(), m.part_of_speech()[0]) for m in self._tokenizer.tokenize(input_text, self._mode)]
        return result

