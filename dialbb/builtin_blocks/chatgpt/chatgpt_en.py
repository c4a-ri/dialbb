#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# chatgpt.py
#   performs English dialogue using ChatGPT

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Any, Tuple, List

from dialbb.builtin_blocks.chatgpt.chatgpt import ChatGPT


class ChatGPT_En(ChatGPT):

    def __init__(self, *args):

        super().__init__(*args)

    def generate_system_utterance(self, dialogue_history: List[Dict[str, str]],
                                  session_id: str, user_id: str,
                                  aux_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any], bool]:
        """
        Generates system utterance using ChatGPT

        :param dialogue_history: list of turn information  [{"speaker": "system", "utterance": <system utterance>},
                                                            {"speaker": "user", "utterance": <user utterance>} ...]
        :param session_id: user id string
        :param user_id: user id string
        :param aux_data: auxiliary data received from main
        :return: a tuple of system utterance string, aux_data as is, and final flag (always False)
        """

        prompt: str = self._prompt_prefix

        for turn in dialogue_history:
            if turn["speaker"] == 'user':
                prompt += f"User: \"{turn['utterance']}\"\n"
            else:
                prompt += f"System: \"{turn['utterance']}\"\n"
        prompt += self._prompt_postfix

        self.log_debug("prompt: " + prompt, session_id=session_id)
        generated_utterance: str = self._generate_with_openai_gpt(prompt)
        self.log_debug("generated system utterance: " + generated_utterance, session_id=session_id)
        system_utterance: str = generated_utterance.replace(f"System:", "").replace('\"', "").replace("'", "").strip()
        self.log_debug("final system utterance: " + system_utterance, session_id=session_id)

        return system_utterance, aux_data, False
