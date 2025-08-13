#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024-2025 C4A Research Institute, Inc.
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
# chatgpt.py
#   performs dialogue using ChatGPT
#   ChatGPTを用いた対話

__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import os
import sys
import traceback
from typing import Dict, Any, List, Union, Tuple
import openai
from dialbb.abstract_block import AbstractBlock
from dialbb.util.error_handlers import abort_during_building

DIALOGUE_HISTORY_OLD_TAG: str = '@dialogue_history'
DIALOGUE_HISTORY_TAG: str = '{dialogue_history}'
DEFAULT_GPT_MODEL: str = "gpt-4o-mini"


class ChatGPT(AbstractBlock):
    """
    performs dialogue using ChatGPT
    """

    def __init__(self, *args):

        super().__init__(*args)

        openai_api_key: str = os.environ.get('OPENAI_API_KEY', os.environ.get('OPENAI_KEY', ""))
        if not openai_api_key:
            abort_during_building("OPENAI_API_KEY is not defined")
        self._openai_client = openai.OpenAI(api_key=openai_api_key)
        self._gpt_model = self.block_config.get("gpt_model", DEFAULT_GPT_MODEL)

        self.user_name: str = self.block_config.get("user_name", "User")
        self.system_name: str = self.block_config.get("system_name", "System")

        # reading prompt template file
        prompt_template_file: str = self.block_config.get("prompt_template", "")
        if not prompt_template_file:
            abort_during_building("prompt template file is not specified")
        filepath: str = os.path.join(self.config_dir, prompt_template_file)
        with open(filepath, encoding='utf-8') as fp:
            self._prompt_template = fp.read()
        if self._prompt_template.find(DIALOGUE_HISTORY_TAG) >= 0 \
           or self._prompt_template.find(DIALOGUE_HISTORY_OLD_TAG) >= 0:
            abort_during_building("The format of the prompt template is obsolete. " +
                                  "The 'dialogue_history' tag is no longer necessary.")

        # temperature
        self._temperature = self.block_config.get("temperature", 0.7)

        # {"session1" : [{"speaker": "user", "utterance": <user utterance>},
        #                {"speaker": "system", "utterance": <system utterance>},
        #                ....]
        # ...}
        self._dialogue_history: Dict[str, List[Dict[str, str]]] = {}

    def process(self, input_data: Dict[str, Any], session_id: str) -> Union[Dict[str, Union[dict, Any]], str]:
        """
        main process of this block

        :param input_data: input to the block. The keys are "user_utterance" (str), "user_id" (str), and "aux_data" (dict)
        :param session_id: session id string
        :return: output from the block. The keys are "system utterance" (str), "aux_data" (dict), and "final" (bool).
        """

        self._user_id = input_data["user_id"]
        if session_id not in self._dialogue_history.keys():  # first turn
            self._dialogue_history[session_id] = []
            system_utterance = self.block_config.get("first_system_utterance")
            aux_data = input_data['aux_data']
            final = False
        else:  # second turn and after
            self._dialogue_history[session_id].append({"speaker": "user", "utterance": input_data["user_utterance"]})
            system_utterance, aux_data, final \
                = self.generate_system_utterance(self._dialogue_history[session_id],
                                                 session_id,
                                                 self._user_id,
                                                 input_data["aux_data"])
        self._dialogue_history[session_id].append({"speaker": "system", "utterance": system_utterance})
        return {"system_utterance": system_utterance,
                "aux_data": aux_data,
                "final": final}

    def _generate_with_openai_gpt(self, messages: List[Dict[str, str]]) -> str:

        """
        Generates system utterance using openai GPT. Does not use "assistant" role.
        This is to be used in the "generate_system_utterance" method.

        :param messages: dialogue history
        :return: generated string
        """

        chat_completion = None
        while True:
            try:
                chat_completion = self._openai_client.with_options(timeout=10).chat.completions.create(
                    model=self._gpt_model,
                    messages=messages,
                    temperature=self._temperature,
                    )
            except openai.APITimeoutError:
                continue
            except Exception as e:
                self.log_error("OpenAI Error: " + traceback.format_exc())
                sys.exit(1)
            finally:
                if not chat_completion:
                    continue
                else:
                    break
        system_utterance: str = chat_completion.choices[0].message.content
        return system_utterance

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

        messages = []
        messages.append({'role': "system", "content": self._prompt_template})

        for turn in dialogue_history:
            if turn["speaker"] == 'user':
                messages.append({'role': "user", "content": turn['utterance']})
            else:
                messages.append({'role': "assistant", "content": turn['utterance']})

        self.log_debug("messages: " + str(messages), session_id=session_id)
        generated_utterance: str = self._generate_with_openai_gpt(messages)
        self.log_debug("generated system utterance: " + generated_utterance, session_id=session_id)
        system_utterance: str = generated_utterance.replace(f'{self.system_name}:', '').strip()
        self.log_debug("final system utterance: " + system_utterance, session_id=session_id)

        return system_utterance, aux_data, False

