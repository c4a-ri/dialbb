#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# abstract_tokenizer.py
#   tokenize input utterance
#   発話を単語分割する組み込みブロック

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from typing import Dict, Any, List
from dialbb.abstract_block import AbstractBlock
from dialbb.main import KEY_SESSION_ID
import dataclasses

KEY_INPUT_TEXT = 'input_text'
KEY_TOKENS = 'tokens'
KEY_TOKENS_WITH_INDICES = 'tokens_with_indices'


@dataclasses.dataclass
class TokenWithIndices:
    """
    token information
    トークン情報
    """
    start: int  # start index in the string  (from <start>-th character)
    end: int  # end index in the string (to <end>-th character)
    form: str  # token string


class AbstractTokenizer(AbstractBlock):

    """
    Abstract Class for TokenizationBlock
    """

    def __init__(self, *args):

        super().__init__(*args)

    def process(self, input_data: Dict[str, Any], session_id: str = "undecided") -> Dict[str, List[str]]:
        """
        tokenize input text
        入力文字列を正規化
        :param input_data: {'input_text': <input text: str>}
        :param session_id: the id of the dialogue session
        :return: output data. {"output_text': tokens: str>}
        """

        session_id = input_data.get(KEY_SESSION_ID, "undecided")  # for logging
        if session_id != "undecided":  # only when used in a dialogue session, not in building
            self.log_debug("input: " + str(input_data), session_id=session_id)
        input_text: str = input_data[KEY_INPUT_TEXT]
        if input_text == "":
            tokens_with_indices = []
        else:
            tokens_with_indices = self.tokenize(input_text)
        tokens = [token_with_indices.form for token_with_indices in tokens_with_indices]
        output = {KEY_TOKENS: tokens, KEY_TOKENS_WITH_INDICES: tokens_with_indices}
        if session_id != "undecided":  # only when used in a dialogue session, not in building
            self.log_debug("output: " + str(output), session_id=session_id)
        return output

    def tokenize(self, input_text: str) -> List[TokenWithIndices]:
        """
        Tokenize input with a tokenizer. To be implemented.
        :param input_text: input text
        :return: list of resulting tokens with indices
        """
        raise NotImplementedError
