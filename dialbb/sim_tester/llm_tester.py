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
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

DEFAULT_GPT_MODEL: str = "gpt-4o-mini"
DIALOGUE_HISTORY_TAG: str = '{dialogue_history}'
DIALOGUE_HISTORY_OLD_TAG: str = '@dialogue_history'
TIMEOUT: int = 10


class LLMTester:

    def __init__(self, test_config: Dict[str, Any]):

        self._debug = False
        if os.environ.get('DIALBB_TESTER_DEBUG', 'no').lower() == "yes":
            self._debug = True

        # conforms to older documents
        if not os.environ.get('OPENAI_API_KEY') and os.environ.get('OPENAI_KEY'):
            os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_KEY')

        self._model = test_config.get("model", DEFAULT_GPT_MODEL)

        self._temperature: float = 0.0
        self._messages: List[Dict[str, str]] = []
        self._dialogue_history = ""
        self._llm_client = None

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

    @staticmethod
    def _convert_message(message: Dict[str, str]):
        role = message["role"]
        content = message["content"]
        if role == "system":
            return SystemMessage(content=content)
        if role == "user":
            return HumanMessage(content=content)
        if role == "assistant":
            return AIMessage(content=content)
        raise ValueError(f"unsupported message role: {role}")

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
        self._messages = []
        self._messages.append({"role": "system", "content": prompt_template})
        self._initialize_llm()

    def generate_next_user_utterance(self, system_utterance: str) -> str:
        """
        generate simulated user utterance following the system utterance
        :param system_utterance: recent system utterance
        :return: generated user utterance
        """

        self._messages.append({"role": "user", "content": system_utterance})

        try:
            response = self._llm_client.invoke(
                [self._convert_message(message) for message in self._messages]
            )
            user_utterance = response.content if hasattr(response, "content") else str(response)
        except Exception:
            traceback.print_exc()
            raise Exception

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

        return self._model
