#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 C4A Research Institute, Inc.
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
# dst_with_llm.py
#   perform dialogue state tracking using various LLMs via LangChain

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import json
import os
import re
import sys
import traceback
from typing import Any, Dict, List, Tuple

import gspread
import pandas as pd
from langchain.chat_models import init_chat_model
from oauth2client.service_account import ServiceAccountCredentials
from pandas import DataFrame

from dialbb.abstract_block import AbstractBlock
from dialbb.builtin_blocks.dst_with_llm.knowledge_converter import convert_dst_knowledge
from dialbb.builtin_blocks.dst_with_llm.prompt_template_en import PROMPT_TEMPLATE_EN
from dialbb.builtin_blocks.dst_with_llm.prompt_template_ja import PROMPT_TEMPLATE_JA
from dialbb.main import CONFIG_KEY_LANGUAGE, KEY_SESSION_ID
from dialbb.util.error_handlers import abort_during_building


CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET: str = "knowledge_google_sheet"
CONFIG_KEY_SHEET_ID: str = "sheet_id"
CONFIG_KEY_KEY_FILE: str = "key_file"
CONFIG_KEY_KNOWLEDGE_FILE: str = "knowledge_file"
CONFIG_KEY_DIALOGUES_SHEET: str = "dialogues_sheet"
CONFIG_KEY_SLOTS_SHEET: str = "slots_sheet"
CONFIG_KEY_PROMPT_TEMPLATE: str = "prompt_template"
CONFIG_KEY_MODEL: str = "model"
CONFIG_KEY_GPT_MODEL: str = "gpt_model"
CONFIG_KEY_TEMPERATURE: str = "temperature"

KEY_DIALOGUE_HISTORY: str = "dialogue_history"
KEY_DST_RESULT: str = "dst_result"

DEFAULT_LLM_MODEL: str = "gpt-4o-mini"
DEFAULT_TEMPERATURE: float = 0.0
LLM_TIMEOUT: int = 10

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CODE_BLOCK_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


class DST(AbstractBlock):
    """
    dialogue state tracker backed by an LLM initialized via LangChain
    """

    def __init__(self, *args):
        super().__init__(*args)

        # language
        self._language = self.config.get(CONFIG_KEY_LANGUAGE, 'en')
        if self._language not in ('en', 'ja'):
            abort_during_building("unsupported language: " + self._language)

        # model and temperature
        self._model = self.block_config.get(CONFIG_KEY_MODEL,DEFAULT_LLM_MODEL)
        self._temperature = self.block_config.get(CONFIG_KEY_TEMPERATURE, DEFAULT_TEMPERATURE)
        try:
            self._llm = init_chat_model(
                self._model,
                temperature=self._temperature,
                timeout=LLM_TIMEOUT,
            )
        except ImportError:
            abort_during_building(
                "langchain and the provider integration packages must be installed. "
                "Required packages depend on the model provider, for example "
                "langchain-openai, langchain-google-genai, or langchain-huggingface."
            )
        except Exception as e:
            abort_during_building(f"Failed to initialize chat model '{self._model}': {e}")

        self.user_name: str = self.block_config.get("user_name", 'ユーザ' if self._language == 'ja' else "User")
        self.system_name: str = self.block_config.get("system_name", 'システム' if self._language == 'ja' else "System")

        dialogues_sheet = self.block_config.get(CONFIG_KEY_DIALOGUES_SHEET, "dialogues")
        slots_sheet = self.block_config.get(CONFIG_KEY_SLOTS_SHEET, "slots")

        prompt_template_file: str = self.block_config.get(CONFIG_KEY_PROMPT_TEMPLATE, "")
        if prompt_template_file:
            prompt_template_path = os.path.join(self.config_dir, prompt_template_file)
            prompt_template = self._read_prompt_template(prompt_template_path)
        elif self._language == 'ja':
            prompt_template = PROMPT_TEMPLATE_JA
        else:
            prompt_template = PROMPT_TEMPLATE_EN

        google_sheet_config: Dict[str, str] = self.block_config.get(CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET)
        if google_sheet_config:
            dialogues_df, slots_df = self._get_dfs_from_gs(google_sheet_config, dialogues_sheet, slots_sheet)
        else:
            excel_file = self.block_config.get(CONFIG_KEY_KNOWLEDGE_FILE)
            if not excel_file:
                abort_during_building(
                    f"Neither knowledge file nor google sheet info is not specified for the block {self.name}."
                )
            dialogues_df, slots_df = self._get_dfs_from_excel(excel_file, dialogues_sheet, slots_sheet)

        # read knowledge from dataframes of excel
        slot_definitions, examples, self.entities2synonyms = convert_dst_knowledge(
            dialogues_df,
            slots_df,
            self.block_config,
            self._language,
        )
        self._prompt_template = prompt_template.replace('{slot_definitions}', slot_definitions).replace('{examples}', examples)


    @staticmethod
    def _read_prompt_template(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _get_dfs_from_gs(self, google_sheet_config: Dict[str, str],
                         utterances_sheet: str, slots_sheet: str) -> Tuple[DataFrame, DataFrame]:
        google_sheet_id: str = google_sheet_config.get(CONFIG_KEY_SHEET_ID)
        key_file: str = os.path.join(self.config_dir, google_sheet_config.get(CONFIG_KEY_KEY_FILE))
        credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file, SCOPES)
        gc = gspread.authorize(credentials)
        workbook = gc.open_by_key(google_sheet_id)
        utterances_data = workbook.worksheet(utterances_sheet).get_all_values()
        slots_data = workbook.worksheet(slots_sheet).get_all_values()
        return pd.DataFrame(utterances_data[1:], columns=utterances_data[0]), \
            pd.DataFrame(slots_data[1:], columns=slots_data[0])

    def _get_dfs_from_excel(self, excel_file: str, utterances_sheet: str, slots_sheet: str) \
            -> Tuple[DataFrame, DataFrame]:
        excel_file_path = os.path.join(self.config_dir, excel_file)
        self.log_debug(f"reading excel file: {excel_file_path}")
        try:
            df_all: Dict[str, DataFrame] = pd.read_excel(excel_file_path, sheet_name=None)
            return df_all.get(utterances_sheet), df_all.get(slots_sheet)
        except Exception as e:
            abort_during_building(f"failed to read excel file: {excel_file_path}. {str(e)}")

    def _stringify_dialogue_history(self, dialogue_history: List[Dict[str, Any]]) -> str:
        dialogue_history_string: str = ""
        for turn in dialogue_history:
            if turn["speaker"] == 'user':
                dialogue_history_string += f"{self.user_name}: {turn['utterance']}\n"
            else:
                dialogue_history_string += f"{self.system_name}: {turn['utterance']}\n"
        return dialogue_history_string

    def process(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        session_id = input_data.get(KEY_SESSION_ID, session_id or "undecided")
        self.log_debug("input: " + str(input_data), session_id=session_id)

        dialogue_history: List[Dict[str, Any]] = input_data.get(KEY_DIALOGUE_HISTORY, [])
        if not dialogue_history:
            dst_result: Dict[str, str] = {}
        else:
            dialogue_history_string: str = self._stringify_dialogue_history(dialogue_history)
            dst_result = self._extract_slots(dialogue_history_string)

        output = {KEY_DST_RESULT: dst_result}
        self.log_debug("output: " + str(output), session_id=session_id)
        return output

    def _get_entity(self, expression: str) -> str:
        """
        get entity from a synonym
        :param expression: expression which may be a synonym of an entity
        :return: entity (or expression as is)
        """
        for entity, synonyms in self.entities2synonyms.items():
            if expression == entity or expression in synonyms:
                return entity
        return expression

    def _extract_slots(self, dialogue_string: str) -> Dict[str, str]:
        """
        Extract slots from dialogue
        :param dialogue_string: stringfied dialogue history
        :return: slot extraction result in the form of  {"<slot name>": "<slot value>", ...}
        """
        prompt = self._prompt_template.replace('{dialogue_history}', dialogue_string)
        self.log_debug("DST prompt " + prompt)

        while True:
            try:
                response = self._llm.invoke(prompt)
                result_text = self._get_response_text(response)
                self.log_debug("LLM result: " + result_text)
                parsed_result = self._parse_llm_result(result_text)
                dst_result: Dict[str, str] = {}
                for slot_name, slot_value in parsed_result.items():
                    if slot_value is None:
                        continue
                    normalized_value = self._get_entity(str(slot_value).strip())
                    if normalized_value:
                        dst_result[str(slot_name)] = normalized_value
                return dst_result
            except TimeoutError:
                continue
            except Exception:
                self.log_error("LLM Error: " + traceback.format_exc())
                sys.exit(1)

    @staticmethod
    def _get_response_text(response: Any) -> str:
        content = response.content if hasattr(response, 'content') else response
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get('text', '')))
                else:
                    parts.append(str(getattr(item, 'text', item)))
            content = ''.join(parts)
        return str(content).strip()

    @staticmethod
    def _parse_llm_result(result_text: str) -> Dict[str, Any]:
        match = CODE_BLOCK_PATTERN.match(result_text)
        if match:
            result_text = match.group(1).strip()
        result: Any = json.loads(result_text)
        if isinstance(result, dict) and isinstance(result.get(KEY_DST_RESULT), dict):
            result = result[KEY_DST_RESULT]
        if not isinstance(result, dict):
            raise ValueError("LLM output must be a JSON object")
        return result
