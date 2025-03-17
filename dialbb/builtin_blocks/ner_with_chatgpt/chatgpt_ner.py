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
# spacey_nlp.py
# chatgpt_ner.py
#   recognize named entities using ChatGPT

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import traceback
import openai
import pandas as pd
from pandas import DataFrame
from dialbb.builtin_blocks.ner_with_chatgpt.knowledge_converter import convert_ner_knowledge, KEY_CLASS, KEY_ENTITY, \
    KEY_RESULT
from dialbb.abstract_block import AbstractBlock
from dialbb.main import CONFIG_KEY_LANGUAGE
from typing import Any, Dict, List, Tuple
import os
import json
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials


from dialbb.main import ANY_FLAG, KEY_SESSION_ID
from dialbb.util.error_handlers import abort_during_building
from dialbb.builtin_blocks.ner_with_chatgpt.prompt_template_ja import PROMPT_TEMPLATE_JA
from dialbb.builtin_blocks.ner_with_chatgpt.prompt_template_en import PROMPT_TEMPLATE_EN


CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET: str = "knowledge_google_sheet"  # google sheet info
CONFIG_KEY_SHEET_ID: str = "sheet_id"  # google sheet id
CONFIG_KEY_KEY_FILE: str = "key_file"  # key file for Google sheets API
CONFIG_KEY_KNOWLEDGE_FILE: str = "knowledge_file"  # Excel file path
CONFIG_KEY_UTTERANCES_SHEET: str = "utterances_sheet"
CONFIG_KEY_CLASSES_SHEET: str = "classes_sheet"
CONFIG_KEY_PROMPT_TEMPLATE: str = "prompt_template"
CONFIG_KEY_GPT_MODEL: str = "gpt_model"

KEY_INPUT_TEXT: str = "input_text"
KEY_AUX_DATA: str = "aux_data"

DEFAULT_GPT_MODEL: str = "gpt-4o-mini"

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']


class NER(AbstractBlock):
    """
    ChatGPT based understander
    """

    def __init__(self, *args):

        super().__init__(*args)

        # chatgpt setting
        openai_api_key: str = os.environ.get('OPENAI_API_KEY', os.environ.get('OPENAI_KEY', ""))
        if not openai_api_key:
            abort_during_building("OPENAI_API_KEY is not defined")
        self._openai_client = openai.OpenAI(api_key=openai_api_key)
        self._gpt_model = self.block_config.get(CONFIG_KEY_GPT_MODEL, DEFAULT_GPT_MODEL)

        # sheets in spreadsheet
        utterances_sheet = self.block_config.get(CONFIG_KEY_UTTERANCES_SHEET, "utterances")
        classes_sheet = self.block_config.get(CONFIG_KEY_CLASSES_SHEET, "classes")

        # language: "en" or "ja"
        self._language = self.config.get(CONFIG_KEY_LANGUAGE, 'en')
        if self._language not in ('en', 'ja'):
            abort_during_building("unsupported language: " + self._language)

        prompt_template_file: str = self.config.get(CONFIG_KEY_PROMPT_TEMPLATE)
        if prompt_template_file:
            prompt_template_file = os.path.join(self.config_dir, prompt_template_file)
            prompt_template: str = self._read_prompt_template(prompt_template_file)
        else:
            if self._language == 'ja':
                prompt_template = PROMPT_TEMPLATE_JA
            else: # english
                prompt_template = PROMPT_TEMPLATE_EN

        google_sheet_config: Dict[str, str] = self.block_config.get(CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET)
        if google_sheet_config:  # get knowledge from google sheet
            utterances_df, slots_df = self._get_dfs_from_gs(google_sheet_config, utterances_sheet, classes_sheet)
        else:  # get knowledge from excel
            excel_file = self.block_config.get(CONFIG_KEY_KNOWLEDGE_FILE)
            if not excel_file:
                abort_during_building(
                    f"Neither knowledge file nor google sheet info is not specified for the block {self.name}.")
            utterances_df, slots_df = self._get_dfs_from_excel(excel_file, utterances_sheet, classes_sheet)

        # convert nlu knowledge to type and slot definitions
        class_list, class_explanations, ne_examples, ner_examples \
            = convert_ner_knowledge(utterances_df, slots_df, self.block_config, language=self._language)
        self._prompt_template = (prompt_template.replace('@classes', class_list)
                                 .replace('@explanations', class_explanations)
                                 .replace('@ne_examples', ne_examples)
                                 .replace('@ner_examples', ner_examples))

    def _read_prompt_template(self, file_path: str) -> str:
        """
        read a file into one string
        :return: the content of the file
        """

        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents: str = file.read()
        return file_contents

    def _get_dfs_from_gs(self, google_sheet_config: Dict[str, str],
                         utterances_sheet: str, slots_sheet: str) \
            -> Tuple[DataFrame, DataFrame]:
        """
        Get DataFrames for each sheet in knowledge in google sheets
        Google sheetに書かれた知識からDataframeを取得する。
        :param google_sheet_config: configuration for accessing google sheet
        :param utterances_sheet: utterances sheet name
        :param slots_sheet: slots sheet name
        :return: (utterances dataframe, slots dataframe, entities dataframe, dictionary dataframe)
        """

        google_sheet_id: str = google_sheet_config.get(CONFIG_KEY_SHEET_ID)
        key_file: str = google_sheet_config.get(CONFIG_KEY_KEY_FILE)
        key_file = os.path.join(self.config_dir, key_file)
        credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file, SCOPES)
        gc = gspread.authorize(credentials)
        workbook = gc.open_by_key(google_sheet_id)
        utterances_data = workbook.worksheet(utterances_sheet).get_all_values()
        slots_data = workbook.worksheet(slots_sheet).get_all_values()
        return pd.DataFrame(utterances_data[1:], columns=utterances_data[0]), \
               pd.DataFrame(slots_data[1:], columns=slots_data[0])

    def _get_dfs_from_excel(self, excel_file: str, utterances_sheet: str, slots_sheet: str)  \
            -> Tuple[DataFrame, DataFrame]:

        """
        Get DataFrames for each sheet in knowledge in Excel
        Excelに書かれた知識からDataframeを取得する。
        :param excel_file: knowledge file excel
        :param utterances_sheet: utterances sheet name
        :param slots_sheet: slots sheet name
        :return: (utterances dataframe, slots dataframe, entities dataframe, dictionary dataframe)
        """

        excel_file_path = os.path.join(self.config_dir, excel_file)
        print(f"reading excel file: {excel_file_path}", file=sys.stderr)
        try:
            df_all: Dict[str, DataFrame] = pd.read_excel(excel_file_path, sheet_name=None)  # read all sheets
            # reading slots sheet
            return df_all.get(utterances_sheet), df_all.get(slots_sheet)
        except Exception as e:
            abort_during_building(f"failed to read excel file: {excel_file_path}. {str(e)}")

    def process(self, input: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        understand input sentence using ChatGPT
        :param input: e.g. {"sentence": "I love egg salad sandwiches"}
        :param session_id: session id sent from client
        :return: {"aux_data": {"NE_<class>": <NE>, "NE_<class>": <NE>, ... <inputted aux data>}}
        """

        session_id: str = input.get(KEY_SESSION_ID, "undecided")
        self.log_debug("input: " + str(input), session_id=session_id)
        input_text = input.get(KEY_INPUT_TEXT, "")
        aux_data: Dict[str, Any] = input.get(KEY_AUX_DATA, {})
        if aux_data is None:
            aux_data = {}
        if input_text == "":
            tentative_result: List[Dict[str, str]] = []
        else:
            tentative_result = self._ner_with_chatgpt(input_text)

        for each_ne in tentative_result:
            class_name: str = "NE_" + each_ne[KEY_CLASS]
            entity: str = each_ne[KEY_ENTITY]
            if aux_data.get(class_name):
                aux_data[class_name] = aux_data[class_name] + ":" + entity
            else:
                aux_data[class_name] = entity

        output = {KEY_AUX_DATA: aux_data}

        return output

    def _ner_with_chatgpt(self, input_text: str) -> List[Dict[str, str]]:
        """
        understand input text using chatgpt
        :param input_text:
        :return: NER result
        """

        prompt: str = self._prompt_template.replace('@input', input_text)
        self.log_debug("NER prompt " + prompt)

        chat_completion = None
        while True:
            try:
                chat_completion = self._openai_client.with_options(timeout=10).chat.completions.create(
                    model=self._gpt_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    response_format={"type": "json_object"}
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
        chatgpt_result_string: str = chat_completion.choices[0].message.content
        self.log_debug("chatgpt result: " + chatgpt_result_string)
        try:
            result: List[Dict[str, str]] = json.loads(chatgpt_result_string)[KEY_RESULT]
            for ne in result:
                if not ne.get(KEY_ENTITY) or not ne.get(KEY_CLASS):
                    raise Exception("NE JSON does not have necessary keys.")
        except Exception as e:
            self.log_warning("ChatGPT's output is not a valid NER result: " + chatgpt_result_string
                             + "Error:" + str(e))
            result: List[Dict[str, Any]] = []  # default result
        return result
