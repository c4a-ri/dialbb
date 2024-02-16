#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# chatgpt_understander.py
#   understand input text using ChatGPT

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import traceback
import openai
import pandas as pd
from pandas import DataFrame
from dialbb.builtin_blocks.understanding_with_chatgpt.knowledge_converter import convert_nlu_knowledge
from dialbb.abstract_block import AbstractBlock
from dialbb.main import CONFIG_KEY_FLAGS_TO_USE, CONFIG_KEY_LANGUAGE
from typing import Any, Dict, List, Tuple
import os
import json
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from snips_nlu import SnipsNLUEngine
from snips_nlu.default_configs import CONFIG_EN, CONFIG_JA

from dialbb.main import ANY_FLAG, KEY_SESSION_ID
from dialbb.util.error_handlers import abort_during_building
from dialbb.builtin_blocks.understanding_with_chatgpt.prompt_templates_ja import PROMPT_TEMPLATE_JA, PROMPT_TEMPLATE_EN


CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET: str = "knowledge_google_sheet"  # google sheet info
CONFIG_KEY_SHEET_ID: str = "sheet_id"  # google sheet id
CONFIG_KEY_KEY_FILE: str = "key_file"  # key file for Google sheets API
CONFIG_KEY_KNOWLEDGE_FILE: str = "knowledge_file"  # excel file path
CONFIG_KEY_UTTERANCE_SHEET: str = "utterances_sheet"
CONFIG_KEY_SLOTS_SHEET: str = "slots_sheet"
CONFIG_KEY_ENTITIES_SHEET: str = "entities_sheet"
CONFIG_KEY_DICTIONARY_SHEET: str = "dictionary_sheet"
CONFIG_KEY_PROMPT_TEMPLATE: str = "prompt_template"
CONFIG_KEY_GPT_MODEL: str = "gpt_model"

KEY_INPUT_TEXT: str = "input_text"
KEY_NLU_RESULT: str = "nlu_result"

DEFAULT_GPT_MODEL: str = "gpt-3.5-turbo"

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']


class Understander(AbstractBlock):
    """
    ChatGPT based understander
    """

    def __init__(self, *args):

        super().__init__(*args)

        # chatgpt setting
        openai_key: str = os.environ.get('OPENAI_KEY', "")
        if not openai_key:
            abort_during_building("OPENAI_KEY is not defined")
        self._openai_client = openai.OpenAI(api_key=openai_key)
        self._gpt_model = self.block_config.get(CONFIG_KEY_GPT_MODEL, DEFAULT_GPT_MODEL)

        # which rows to use
        flags_to_use = self.block_config.get(CONFIG_KEY_FLAGS_TO_USE, [ANY_FLAG])

        # sheets in spreadsheet
        utterances_sheet = self.block_config.get(CONFIG_KEY_UTTERANCE_SHEET, "utterances")
        slots_sheet = self.block_config.get(CONFIG_KEY_SLOTS_SHEET, "slots")
        dictionary_sheet = self.block_config.get(CONFIG_KEY_DICTIONARY_SHEET, "dictionary")

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
            utterances_df, slots_df, dictionary_df \
                = self._get_dfs_from_gs(google_sheet_config, utterances_sheet, slots_sheet, dictionary_sheet)
        else:  # get knowledge from excel
            excel_file = self.block_config.get(CONFIG_KEY_KNOWLEDGE_FILE)
            if not excel_file:
                abort_during_building(
                    f"Neither knowledge file nor google sheet info is not specified for the block {self.name}.")
            utterances_df, slots_df, dictionary_df \
                = self._get_dfs_from_excel(excel_file, utterances_sheet, slots_sheet, dictionary_sheet)

        # convert nlu knowledge to type and slot definitions
        types, slot_definitions, examples, self.entities2synonyms \
            = convert_nlu_knowledge(utterances_df, slots_df, flags_to_use, language=self._language)
        self._prompt_template = prompt_template.replace('@examples', examples).replace('@types', types)\
            .replace('@slot_definitions', slot_definitions)

    def _read_prompt_template(self, file_path: str) -> str:
        """
        read a file into one string
        :return: the content of the file
        """

        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents: str = file.read()
        return file_contents

    def _get_dfs_from_gs(self, google_sheet_config: Dict[str, str],
                         utterances_sheet: str, slots_sheet: str,
                         dictionary_sheet: str) \
            -> Tuple[DataFrame, DataFrame, DataFrame]:
        """
        Get DataFrames for each sheet in knowledge in google sheets
        Google sheetに書かれた知識からDataframeを取得する。
        :param google_sheet_config: configuration for accessing google sheet
        :param utterances_sheet: utterances sheet name
        :param slots_sheet: slots sheet name
        :param dictionary_sheet: dictionary sheet name
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
        dictionary_data = workbook.worksheet(dictionary_sheet).get_all_values()
        return pd.DataFrame(utterances_data[1:], columns=utterances_data[0]), \
               pd.DataFrame(slots_data[1:], columns=slots_data[0]), \
               pd.DataFrame(dictionary_data[1:], columns=dictionary_data[0])

    def _get_dfs_from_excel(self, excel_file: str, utterances_sheet: str, slots_sheet: str, dictionary_sheet: str):

        """
        Get DataFrames for each sheet in knowledge in Excel
        Excelに書かれた知識からDataframeを取得する。
        :param excel_file: knowledge file excel
        :param utterances_sheet: utterances sheet name
        :param slots_sheet: slots sheet name
        :param dictionary_sheet: dictionary sheet name
        :return: (utterances dataframe, slots dataframe, entities dataframe, dictionary dataframe)
        """

        excel_file_path = os.path.join(self.config_dir, excel_file)
        print(f"reading excel file: {excel_file_path}", file=sys.stderr)
        try:
            df_all: Dict[str, DataFrame] = pd.read_excel(excel_file_path, sheet_name=None)  # read all sheets
            # reading slots sheet
            return df_all.get(utterances_sheet), df_all.get(slots_sheet), df_all.get(dictionary_sheet)
        except Exception as e:
            abort_during_building(f"failed to read excel file: {excel_file_path}. {str(e)}")

    def process(self, input: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        understand input sentence using SNIPS. when num_candidates in config is more than 1,
        n-best results are returned
        SNIPSを用いて言語理解を行う
        コンフィギュレーションのnum_candidatesが2以上なら、n-bestの言語理解結果が返される
        :param input: e.g. {"sentence": "I love egg salad sandwiches"}
        :param session_id: session id sent from client
        :return: {"nlu_result": <nlu result in DialBB format>} or
                 {"nlu_result": <list of nlu results in DialBB format>}
                 e.g., {"nlu_result": {"type": "tell_favorite_sandwiches",
                                       "slots": {"sandwich": "egg salad sandwich"}}}
                        or
                        {"nlu_result": [{"type": "tell_favorite_sandwiches",
                                         "slots": {"sandwich": "egg salad sandwich"}}
                                         ...
                                         {"type": ...,
                                         "slots": {...}}]
        """

        session_id: str = input.get(KEY_SESSION_ID, "undecided")
        self.log_debug("input: " + str(input), session_id=session_id)
        input_text = input.get(KEY_INPUT_TEXT, "")
        if input_text == "":
            nlu_result: Dict[str, Any] = {"type": "", "slots": {}}
        else:
            nlu_result = self._understand_with_chatgpt(input_text)

        output = {KEY_NLU_RESULT: nlu_result}
        self.log_debug("output: " + str(output), session_id=session_id)

        return output

    def _understand_with_chatgpt(self, input_text: str) -> Dict[str, Any]:
        """
        understand input text using chatgpt
        :param input_text:
        :return:
        """

        prompt: str = self._prompt_template.replace('@input', input_text)
        chat_completion = None
        while True:
            try:
                chat_completion = self._openai_client.with_options(timeout=10).chat.completions.create(
                    model=self._gpt_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
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

        try:
            result: Dict[str, Any] = json.loads(chatgpt_result_string)
            if not result.get("type"):
                raise Exception("result doesn't have type")
            if not result.get("slots") or type(result.get("slots")) != dict:
                raise Exception("result doesn't have valid slots")
        except Exception:
            self.log_warning("ChatGPT's output is not a valid understanding result: " + chatgpt_result_string)
            result: Dict[str, Any] = {"type": "", "slots": {}}  # default result
        return result
























