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
