#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 C4A Research Institute, Inc.
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
#
# llm_tester.py
#   Tester using LLM-based simulation
#   LLMを利用したシミュレーションによるテスタ



import os, sys
import traceback

import openai
import google.generativeai as genai
from typing import Dict, Any, List

DEFAULT_GPT_MODEL: str = "gpt-4o-mini"
DIALOGUE_HISTORY_TAG: str = '{dialogue_history}'
DIALOGUE_HISTORY_OLD_TAG: str = '@dialogue_history'
TIMEOUT: int = 10

class LLMTester:

    def __init__(self, test_config: Dict[str, Any]):

        self._debug = False
        if os.environ.get('DIALBB_TESTER_DEBUG', 'no').lower() == "yes":
            self._debug = True

        self._llm_type = test_config.get("llm_type", "chatgpt")
        self._llm = test_config.get("model", "")

        if self._llm_type == "chatgpt":

            openai_key: str = os.environ.get('OPENAI_KEY', os.environ.get('OPENAI_API_KEY', ""))
            if not openai_key:
                print("environment variable OPENAI_KEY or OPENAI_API_KEY is not defined.")
                sys.exit(1)
            self._openai_client = openai.OpenAI(api_key=openai_key)
            openai.api_key = openai_key
            self._gpt_model: str = test_config.get("model", DEFAULT_GPT_MODEL)

        else:

            print("unsupported llm type: " + self._llm_type)
            sys.exit(1)

        self._temperature: float = 0.0
        self._messages: List[Dict[str, str]] = []
        self._user_name_string: str = test_config.get("user_name", "User")
        self._system_name_string: str = test_config.get("system_name", "System")
        self._dialogue_history = ""

    def set_parameters_and_clear_history(self, prompt_template: str, temperature: float) -> None:
        """
        setting simulator parameters
        :param prompt_template: template of prompt to be used in calling ChatGPT
        :param temperature: temperature for GPT
        :return: None
        """

        # check old prompt
        if prompt_template.find(DIALOGUE_HISTORY_TAG) >= 0 \
           or prompt_template.find(DIALOGUE_HISTORY_OLD_TAG) >= 0:
            print("The format of the prompt template is obsolete. The 'dialogue_history' tag is no longer necessary.")
            sys.exit(1)

        self._temperature = temperature
        self._messages.append({"role": "system", "content": prompt_template})

    def generate_next_user_utterance(self, system_utterance: str) -> str:
        """
        generate simulated user utterance following the system utterance
        :param system_utterance: recent system utterance
        :return: generated user utterance
        """

        self._messages.append({"role": "user", "content": system_utterance})

        if self._llm_type == 'chatgpt':

            chat_completion = None
            while True:
                try:
                    chat_completion = self._openai_client.with_options(timeout=TIMEOUT).chat.completions.create(
                        model=self._gpt_model,
                        messages=self._messages,
                        temperature=self._temperature,
                        )
                except openai.APITimeoutError:
                    continue
                except Exception as e:
                    traceback.print_exc()
                    raise Exception
                finally:
                    if not chat_completion:
                        continue
                    else:
                        break
            user_utterance: str = chat_completion.choices[0].message.content

        elif self._llm_type == 'gemini':

            raise Exception("gemini can't be used.")  # this won't occur

        print(f"generated user utterance: {user_utterance}")
        user_utterance = user_utterance.replace('"','')
        self._messages.append({"role": "assistant", "content": user_utterance})

        return user_utterance

    def get_llm_model(self) -> str:
        """
        returns gpt model name for logging
        :return:
        :rtype:
        """

        return self._llm
