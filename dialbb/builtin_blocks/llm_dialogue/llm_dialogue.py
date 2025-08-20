#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# llm_dialogue.py
#   performs dialogue using LangChain.
#   LangChainでLLMを用いた対話

__version__ = "0.1"
__author__ = "Mikio Nakano"
__copyright__ = "C4A Research Institute, Inc."

import os
import sys
import traceback
from typing import Dict, Any, List, Union, Tuple
from dialbb.abstract_block import AbstractBlock
from dialbb.util.error_handlers import abort_during_building
from dialbb.builtin_blocks.llm_dialogue.llm_selector import llm_selector

from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

DEFAULT_GPT_MODEL: str = "gpt-3.5-turbo"


class LLMDialogue(AbstractBlock):
    """
    performs dialogue using  LangChain and ChatGPT.
    """

    def __init__(self, *args):
        super().__init__(*args)

        # Configより各設定データを読み込み
        self._gpt_model = self.block_config.get("gpt_model", DEFAULT_GPT_MODEL)

        # TODO: How to set API_KEY for each LLM?

        self.user_name: str = self.block_config.get("user_name", "User")
        self.system_name: str = self.block_config.get("system_name", "System")

        prompt_template_file = self.block_config.get("prompt_template", "")
        if not prompt_template_file:
            abort_during_building("prompt template file is not specified")
        filepath: str = os.path.join(self.config_dir, prompt_template_file)
        with open(filepath, encoding="utf-8") as fp:
            self._prompt_template = fp.read()

        # LLMモデルを生成
        llm_type = self.block_config.get("llm_type", "chatgpt")
        llm_model = self.block_config.get("llm_model", "")
        print(f"{llm_type=} : {llm_model=}")
        llm = llm_selector(llm_type, llm_model)
        print(f"LLM type : {type(llm)}")

        # 出力結果のOutput Parserを定義
        parser = StrOutputParser()

        # PromptTemplateの定義
        prompt = ChatPromptTemplate.from_messages(
            [
                # 毎回必ず含まれるSystemプロンプトを追加
                SystemMessage(content=self._prompt_template),
                # ChatMessageHistory(BufferMemory)をプロンプトに追加
                MessagesPlaceholder(variable_name="history"),
                # ユーザーの入力をプロンプトに追加
                HumanMessagePromptTemplate.from_template("{utterance}"),
            ]
        )

        # Chainを構成
        chain = prompt | llm | parser

        # 対話履歴のMemoryを定義
        self._history_buffer = {}

        # RunnableWithMessageHistoryの準備
        self.chat_model = RunnableWithMessageHistory(
            chain,
            self._get_session_history,
            input_messages_key="utterance",
            history_messages_key="history",
        )

    def process(
        self, input_data: Dict[str, Any], session_id: str
    ) -> Union[Dict[str, Union[dict, Any]], str]:
        """
        main process of this block

        :param input_data: input to the block. The keys are "user_utterance" (str), "user_id" (str), and "aux_data" (dict)
        :param session_id: session id string
        :return: output from the block. The keys are "system utterance" (str), "aux_data" (dict), and "final" (bool).
        """

        self._user_id = input_data["user_id"]
        if session_id not in self._history_buffer:  # first turn
            system_utterance = self.block_config.get("first_system_utterance")
            aux_data = input_data["aux_data"]
            final = False
            history = self._get_session_history(session_id)
            history.add_ai_message(system_utterance)
        else:  # second turn and after
            system_utterance, aux_data, final = self.generate_system_utterance(
                session_id,
                self._user_id,
                input_data["aux_data"],
                input_data["user_utterance"],
            )

        return {
            "system_utterance": system_utterance,
            "aux_data": aux_data,
            "final": final,
        }

    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """
        Management of dialogue history for each session

        :param session_id: user id string
        :return: dialogue history buffer

        Example of dialogue history data format.
          {"session1" : [{"Human": <user utterance>},
                         {"AI": <system utterance>},
                         ....]
          ...}
        """
        # セッションIDごとの会話履歴の取得
        if session_id not in self._history_buffer:
            self._history_buffer[session_id] = ChatMessageHistory()
        return self._history_buffer[session_id]

    def generate_system_utterance(
        self,
        session_id: str,
        user_id: str,
        aux_data: Dict[str, Any],
        user_utterance: str,
    ) -> Tuple[str, Dict[str, Any], bool]:
        """
        Generates system utterance using ChatGPT

        :param dialogue_history: list of turn information  [{"speaker": "system", "utterance": <system utterance>},
                                                            {"speaker": "user", "utterance": <user utterance>} ...]
        :param session_id: user id string
        :param user_id: user id string
        :param aux_data: auxiliary data received from main
        :return: a tuple of system utterance string, aux_data as is, and final flag (always False)
        """
        self.log_debug(
            f"history_buffe: {self._history_buffer[session_id]}", session_id=session_id
        )

        system_utterance = ""
        while True:
            try:
                # ChatModelの実行
                system_utterance = self.chat_model.invoke(
                    {"utterance": user_utterance},
                    config={"configurable": {"session_id": session_id}},
                )
            except Exception as e:
                self.log_error("LangChain Error: " + traceback.format_exc())
                sys.exit(1)
            finally:
                if not system_utterance:
                    continue
                else:
                    break

        self.log_debug(
            "final system utterance: " + system_utterance, session_id=session_id
        )
        return system_utterance, aux_data, False
