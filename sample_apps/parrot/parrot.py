#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# parrot.py
#   simple echoing application

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


from dialbb.abstract_block import AbstractBlock
from typing import List, Any, Dict, Tuple


class Parrot(AbstractBlock):

    def __init__(self, *args):
        super().__init__(*args)

    def process(self, input: Dict[str, Any], initial=False) -> Dict[str, Any]:
        """
        :param input. keys: "input_text", "input_aux_data"
        :return: output. keyss: "output_text", "output_aux_data"
        """

        self.log_debug("input: " + str(input))
        if initial:
            system_utterance = "こちらはオウム返しbotです。何でも言って見てください。"
            output = {"output_text": system_utterance, "output_aux_data": {}, "final": False}
        else:
            user_utterance = input['input_text']
            input_aux_data = input['input_aux_data']
            system_utterance = f"「{user_utterance}」と仰いましたね。"
            output = {"output_text": system_utterance, "output_aux_data": input_aux_data, "final": False}
        self.log_debug("output: " + str(output))
        return output
