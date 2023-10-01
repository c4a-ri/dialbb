#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# chatgpt.py
#   performs dialogue using ChatGPT
#   ChatGPTを用いた対話

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import os
import re
from typing import Dict, Any, List, Union, Tuple
import openai
from dialbb.abstract_block import AbstractBlock
from dialbb.util.error_handlers import abort_during_building

DEFAULT_GPT_MODEL: str = "gpt-3.5-turbo"


class ChatGptMp(AbstractBlock):
    """
    performs dialogue using ChatGPT
    """

    def __init__(self, *args):

        super().__init__(*args)

        openai_key: str = os.environ.get('OPENAI_KEY', "")
        if not openai_key:
            abort_during_building("OPENAI_KEY is not defined")
        openai.api_key = openai_key
        self._gpt_model = self.block_config.get("gpt_model", DEFAULT_GPT_MODEL)

        # read prefix and postfix
        self._system_personality: str = self.block_config.get("system_personality", "")
        self._prompt_postfix: str = self.block_config.get("prompt_postfix", "")
        self._silence: str = self.block_config.get("silence", "")
        self._my_name = self.config.get('my_name')
        if not self._my_name:
            abort_during_building("name of this participant is not given")

        # {"sesion1" : [{"speaker": "user", "utterance": <user utterance>},
        #                {"speaker": "system", "utterance": <system utterance>},
        #                ....]
        # ...}
        self._dialogue_history: Dict[str, List[Dict[str, str]]] = {}
        self._utterance_pattern = re.compile(r'「([^」]+)」')



    def process(self, input_data: Dict[str, Any], session_id: str) -> Union[Dict[str, Union[dict, Any]], str]:
        """
        main process of this block

        :param input_data: input to the block. The keys are "user_utterance" (str), "user_id" (str), and "aux_data" (dict)
        :param session_id: session id string
        :return: output from the block. The keys are "system utterance" (str), "aux_data" (dict), and "final" (bool).
        """

        if session_id not in self._dialogue_history.keys():  # first turn
            self._dialogue_history[session_id] = []
            system_utterance = self.block_config.get("initial_utterance", "")
            if system_utterance:
                self._dialogue_history[session_id].append({"speaker": "あなた",
                                                           "utterance": system_utterance})
            aux_data = input_data['aux_data']
            final = False
        else:  # second turn and after
            if input_data["user_utterance"]:
                self._dialogue_history[session_id].append({"speaker": input_data["user_id"],
                                                           "utterance": input_data["user_utterance"]})
            system_utterance, aux_data, final \
                = self.generate_system_utterance(self._dialogue_history[session_id],
                                                 session_id,
                                                 self._my_name,
                                                 input_data["aux_data"])
        if system_utterance == self._silence:
            system_utterance = ""
        if system_utterance:
            self._dialogue_history[session_id].append({"speaker": "あなた", "utterance": system_utterance})
        return {"system_utterance": system_utterance,
                "aux_data": aux_data,
                "final": final}

    def _generate_with_openai_gpt(self, prompt: str) -> str:

        """
        Generates system utterance using OpenAI GPT. Does not use "assistant" role.
        This is to be used in the "generate_system_utterance" method.

        :param prompt: prompt string
        :return: generated string
        """

        # call OpenAI API
        response = openai.ChatCompletion.create(
            model=self._gpt_model,
            messages=[
                {"role": "user", "content": prompt}]
        )
        return response.choices[0]['message']['content']

    def generate_system_utterance(self, dialogue_history: List[Dict[str, str]],
                                  session_id: str, my_name: str,
                                  aux_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any], bool]:
        """
        Generates system utterance using ChatGPT

        :param dialogue_history: list of turn information  [{"speaker": "system", "utterance": <system utterance>},
                                                            {"speaker": "user", "utterance": <user utterance>} ...]
        :param session_id: session id string
        :param my_name: participant name string
        :param aux_data: auxiliary data received from main
        :return: a tuple of system utterance string, aux_data as is, and final flag (always False)
        """
        prompt = f"あなたの名前は{my_name}です。" + self._system_personality
        for turn in dialogue_history:
            prompt += f"{turn['speaker']}「{turn['utterance']}」\n"
        prompt += self._prompt_postfix

        self.log_debug("prompt: " + prompt, session_id=session_id)
        generated_utterance: str = self._generate_with_openai_gpt(prompt)
        self.log_debug("generated system utterance: " + generated_utterance, session_id=session_id)
        m = self._utterance_pattern.search(generated_utterance)
        if m:
            system_utterance: str = m.group(1)
        else:
            system_utterance: str = generated_utterance
        self.log_debug("final system utterance: " + system_utterance, session_id=session_id)

        return system_utterance, aux_data, False
