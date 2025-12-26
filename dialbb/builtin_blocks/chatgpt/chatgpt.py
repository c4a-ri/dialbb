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
import datetime
from typing import Dict, Any, List, Union, Tuple
import openai
from dialbb.abstract_block import AbstractBlock
from dialbb.builtin_blocks.util import extract_aux_data
from dialbb.util.error_handlers import abort_during_building
import re

from dialbb.util.globals import CHATGPT_INSTRUCTIONS

DIALOGUE_HISTORY_OLD_TAG: str = '@dialogue_history'
DIALOGUE_HISTORY_TAG: str = '{dialogue_history}'
CURRENT_TIME_TAG: str = '{current_time}'
DEFAULT_GPT_MODEL: str = "gpt-4o-mini"
DIALOGUE_UP_TO_NOW = {"ja": "現在までの対話", "en": "Dialogue up to now"}


#  [[[....{tag1}....{tag2}....]]]
REMAINING_TAGS_PATTERN = re.compile( r"\[\[\[(?=.*\{[A-Za-z0-9_]+\})(?:[^\{\]]|\{[A-Za-z0-9_]+\})*\]\]\]",
                                     re.DOTALL)


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

        self._language = self.config.get("language", 'en')
        self._instruction = self.block_config.get("instruction", CHATGPT_INSTRUCTIONS[self._language])

        self.user_name: str = self.block_config.get("user_name", 'ユーザ' if self._language == 'ja' else "User")
        self.system_name: str = self.block_config.get("system_name", 'システム' if self._language == 'ja' else "System")

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

    def process(self, input_data: Dict[str, Any], session_id: str) -> Union[Dict[str, Union[dict, Any]], str]:
        """
        main process of this block

        :param input_data: input to the block. The keys are "user_utterance" (str), "user_id" (str), and "aux_data" (dict)
        :param session_id: session id string
        :return: output from the block. The keys are "system utterance" (str), "aux_data" (dict), and "final" (bool).
        """

        dialogue_history = input_data.get("dialogue_history")
        if not dialogue_history:
            self.log_error("dialogue_history is not specified as input in the block configuration.")

        aux_data = input_data.get("aux_data", {})
        if aux_data is None:
            aux_data = {}
        if len(dialogue_history) == 1:
            system_utterance = self.block_config.get("first_system_utterance")
            aux_data = input_data.get('aux_data', {})
            final = False
        else:  # second turn and after
            system_utterance, aux_data, final = self.generate_system_utterance(dialogue_history, aux_data, session_id)
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
                temperature = 1 if self._gpt_model == 'gpt-5' else self._temperature
                chat_completion = self._openai_client.with_options(timeout=10).chat.completions.create(
                    model=self._gpt_model,
                    messages=messages,
                    temperature=temperature
                    )
            except openai.APITimeoutError:
                continue
            except Exception as e:
                self.log_error("OpenAI Error: " + traceback.format_exc())
                sys.exit(1)
            else:
                if not chat_completion:
                    continue
                else:
                    break
        system_utterance: str = chat_completion.choices[0].message.content
        return system_utterance

    @staticmethod
    def get_current_time_string(language: str) -> str:
        """
        generates string to represent current string.
        :param language:
        :return:
        """

        now = datetime.datetime.now()
        if language == 'ja':
            weekdays = ["月", "火", "水", "木", "金", "土", "日"]
            date_str = now.strftime("%Y年%m月%d日")
            time_str = now.strftime("%H時%M分%S秒")
            weekday_str = weekdays[now.weekday()]
            result: str = f"{date_str}（{weekday_str}） {time_str}"
        else:
            result = now.strftime("%A, %B %d, %Y %I:%M:%S %p")
        return result

    def generate_system_utterance(
            self,
            dialogue_history: List[Dict[str, str]],
            aux_data: Dict[str, Any],
            session_id: str
    ) -> Tuple[str, Dict[str, Any], bool]:

        """
        Generates system utterance using ChatGPT

        :param dialogue_history: list of turn information  [{"speaker": "system", "utterance": <system utterance>},
                                                            {"speaker": "user", "utterance": <user utterance>} ...]
        :param aux_data: auxiliary data received from main
        :param session_id: session ID
        :return: a tuple of system utterance string, aux_data as is, and final flag (always False)
        """

        language = self.config.get("langauge", 'en')
        prompt = self._prompt_template
        prompt = prompt.replace(CURRENT_TIME_TAG, self.get_current_time_string(language))  # {current_time}
        if aux_data:
            for aux_data_key, aux_data_value in aux_data.items():  # aux_data values replace their place holders
                prompt = prompt.replace("{" + aux_data_key + "}", str(aux_data_value))
        prompt = REMAINING_TAGS_PATTERN.sub("", prompt)  # remove remaining tags enclosed by [[[ .... ]]]]
        prompt = prompt.replace('[[[', "")  # remove remaining brackets
        prompt = prompt.replace(']]]', "")

        # add dialogue history to string
        dialogue_history_string: str = ""
        for turn in dialogue_history:
            if turn["speaker"] == 'user':
                dialogue_history_string += f"{self.user_name}: {turn['utterance']}\n"
            else:
                dialogue_history_string += f"{self.system_name}: {turn['utterance']}\n"

        if prompt.find(DIALOGUE_HISTORY_TAG) >= 0:
            prompt: str = self._prompt_template.replace(DIALOGUE_HISTORY_TAG, dialogue_history_string)
        elif prompt.find(DIALOGUE_HISTORY_OLD_TAG) >= 0:
            prompt: str = prompt.replace(DIALOGUE_HISTORY_OLD_TAG, dialogue_history_string)
        else:
            prompt += f"\n#{DIALOGUE_UP_TO_NOW[language]}\n\n{dialogue_history_string}"

        # create messages
        messages = []
        messages.append({'role': "system", "content": self._instruction})
        messages.append({'role': "user", "content": prompt})
        self.log_debug("messages: " + str(messages), session_id=session_id)

        generated_utterance: str = self._generate_with_openai_gpt(messages)
        self.log_debug("generated system utterance: " + generated_utterance, session_id=session_id)
        system_utterance: str = generated_utterance.replace(f'{self.system_name}:', '').strip()
        self.log_debug("final system utterance: " + system_utterance, session_id=session_id)

        # update aux data using (key:value, key:value, ...) at the end of system utterance
        system_utterance, aux_data_to_update = extract_aux_data(system_utterance)
        aux_data.update(aux_data_to_update)

        return system_utterance, aux_data, False

