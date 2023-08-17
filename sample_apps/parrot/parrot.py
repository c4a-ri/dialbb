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
        self._known_sessions: Dict[str, bool] = {}  # session_id -> True

    def process(self, input: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        :param input. keys: "input_text", "input_aux_data"
        :param session_id: session id string.
        :return: output. keys: "output_text", "output_aux_data"
        """

        self.log_debug("input: " + str(input))
        continuing_session: bool = self._known_sessions.get(session_id, False)
        if not continuing_session:
            self._known_sessions[session_id] = True
            system_utterance = "I'm a parrot. You can say anything."
            output = {"output_text": system_utterance, "output_aux_data": {}, "final": False, "session_id": session_id}
        else:
            user_utterance = input['input_text']
            input_aux_data = input['input_aux_data']
            system_utterance = f'You said "{user_utterance}"'
            output = {"output_text": system_utterance, "output_aux_data": input_aux_data, "final": False, "session_id": session_id}
        self.log_debug("output: " + str(output))
        return output
