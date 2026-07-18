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

import os
import sys
import traceback
from typing import Dict, Any, List
from langchain.chat_models import init_chat_model
from dialbb.util.globals import CHATGPT_INSTRUCTIONS

DEFAULT_GPT_MODEL: str = "gpt-5.4-nano"
DIALOGUE_HISTORY_TAG: str = '{dialogue_history}'
DIALOGUE_HISTORY_OLD_TAG: str = '@dialogue_history'
TIMEOUT: int = 10


class LLMTester:

    def __init__(self, test_config: Dict[str, Any]):

        self._debug = False
        if os.environ.get('DIALBB_TESTER_DEBUG', 'no').lower() == "yes":
            self._debug = True

        self._model = test_config.get("model", DEFAULT_GPT_MODEL)

        self._temperature: float = 0.0
        self._dialogue_history = ""
        self._llm_client = None
        self._language: str = test_config.get("language", 'en')
        if self._language == 'en':
            self._user_name: str = "User"
            self._system_name: str = "System"
            self._dialogue_history_tag: str = "# Dialogue up to now"
        elif self._language == 'ja':
            self._user_name = "ユーザ"
            self._system_name = "システム"
            self._dialogue_history_tag: str = "# 今までの対話"
        else:
            raise Exception("Unsupported language: " + self._language)
        self._instruction = CHATGPT_INSTRUCTIONS[self._language]

    def _initialize_llm(self) -> None:
        try:
            if self._model.startswith("gpt-5") or self._model.startswith("openai:gpt-5"):
                print("Note that temperature can't be specified for GPT-5x.")
                self._llm_client = init_chat_model(
                    self._model,
                    timeout=TIMEOUT,
                )
            else:
                self._llm_client = init_chat_model(
                    self._model,
                    temperature=self._temperature,
                    timeout=TIMEOUT,
                )
        except Exception as exc:
            print(f"failed to initialize chat model '{self._model}': {exc}")
            sys.exit(1)

    def set_parameters_and_clear_history(self, temperature: float) -> None:
        """
        setting simulator parameters
        :param temperature: temperature for GPT
        :return: None
        """

        self._temperature = temperature
        self._dialogue_history = ""
        self._initialize_llm()

    def generate_next_user_utterance(self, prompt_template: str, system_utterance: str) -> str:
        """
        generate simulated user utterance following the system utterance
        :param prompt_template: prompt template
        :param system_utterance: recent system utterance
        :return: generated user utterance
        """

        self._dialogue_history += f"{self._system_name}: {system_utterance}\n"
        messages = []
        messages.append({'role': "system", "content": self._instruction})
        prompt = prompt_template + "\n\n" + self._dialogue_history_tag + "\n\n" + self._dialogue_history
        if self._debug:
            print(prompt)
        messages.append({'role': "user", "content": prompt})

        try:
            print(f"dialogue history={self._dialogue_history}")
            response = self._llm_client.invoke(messages)
            print(f"response={str(response)}")
            user_utterance = response.content if hasattr(response, "content") else str(response)
        except Exception:
            traceback.print_exc()
            raise Exception

        print(f"generated user utterance: {user_utterance}")
        user_utterance = user_utterance.replace('"','')
        self._dialogue_history += f"{self._user_name}: {user_utterance}\n"

        return user_utterance

    def get_llm_model(self) -> str:
        """
        returns gpt model name for logging
        :return:
        :rtype:
        """

        return self._model
