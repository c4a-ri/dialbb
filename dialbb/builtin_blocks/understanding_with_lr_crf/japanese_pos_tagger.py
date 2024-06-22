#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

