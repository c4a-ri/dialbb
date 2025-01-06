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
# english_pos_tagger.py
#   tokenize input utterance with NLTK for LR-CRF understander

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from typing import Dict, Any, List, Tuple
import nltk
from nltk.tokenize import word_tokenize

class EnglishPosTagger:

    """
    Japanese Tokenizer
    """

    def __init__(self):


        # download tagger
        nltk.download('averaged_perceptron_tagger')
        nltk.download('punkt')

    def tag(self, input_text: str) -> List[Tuple[str, str]]:

        """
        tokenizes input with NLTK and tags POS labels
        :param input_text: text to tokenize
        :return: list of Tuples of tokens and pos e.g., [(word, pos), (word, pos) ...]
        """

        tokens: List[str] = word_tokenize(input_text)
        tagged_tokens: List[Tuple[str, str]] = nltk.pos_tag(tokens)

        return tagged_tokens



