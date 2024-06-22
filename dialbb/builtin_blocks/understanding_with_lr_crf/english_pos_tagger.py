#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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



