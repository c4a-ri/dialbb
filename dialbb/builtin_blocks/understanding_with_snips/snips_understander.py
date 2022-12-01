#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# snips_understander.py
#   understand input text using snips nlu

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import importlib
from types import ModuleType

import pandas as pd
from pandas import DataFrame
from dialbb.builtin_blocks.understanding_with_snips.knowledge_converter import convert_nlu_knowledge
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
from dialbb.builtin_blocks.util.sudachi_tokenizer import SudachiTokenizer, Token

SNIPS_SEED = 42  # from SNIPS tutorial

CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET: str = "knowledge_google_sheet"  # google sheet info
CONFIG_KEY_SHEET_ID: str = "sheet_id"  # google sheet id
CONFIG_KEY_KEY_FILE: str = "key_file"  # key file for Google sheets API
CONFIG_KEY_KNOWLEDGE_FILE: str = "knowledge_file"  # excel file path
CONFIG_KEY_UTTERANCE_SHEET: str = "utterances_sheet"
CONFIG_KEY_SLOTS_SHEET: str = "slots_sheet"
CONFIG_KEY_ENTITIES_SHEET: str = "entities_sheet"
CONFIG_KEY_DICTIONARY_SHEET: str = "dictionary_sheet"
CONFIG_KEY_SUDACHI_NORMALIZATION: str = "sudachi_normalization"
CONFIG_KEY_NUM_CANDIDATES: str = "num_candidates"
KEY_INPUT_TEXT: str = "input_text"
KEY_NLU_RESULT: str = "nlu_result"
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']


class Understander(AbstractBlock):
    """
    SNIPS based understander
    """

    def __init__(self, *args):

        super().__init__(*args)

        flags_to_use = self.block_config.get(CONFIG_KEY_FLAGS_TO_USE, [ANY_FLAG])

        utterances_sheet = self.block_config.get(CONFIG_KEY_UTTERANCE_SHEET, "utterances")
        slots_sheet = self.block_config.get(CONFIG_KEY_SLOTS_SHEET, "slots")
        entities_sheet = self.block_config.get(CONFIG_KEY_ENTITIES_SHEET, "entities")
        dictionary_sheet = self.block_config.get(CONFIG_KEY_DICTIONARY_SHEET, "dictionary")
        self._language = self.config[CONFIG_KEY_LANGUAGE]
        self._num_candidates = self.block_config.get(CONFIG_KEY_NUM_CANDIDATES, 1)
        if type(self._num_candidates) != int or self._num_candidates < 1:
            abort_during_building(f"value of {CONFIG_KEY_NUM_CANDIDATES} must be a natural number.")

        google_sheet_config: Dict[str, str] = self.block_config.get(CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET)
        if google_sheet_config:  # get knowledge from google sheet
            utterances_df, slots_df, entities_df, dictionary_df \
                = self.get_dfs_from_gs(google_sheet_config, utterances_sheet, slots_sheet,
                                       entities_sheet, dictionary_sheet)
        else:  # get knowledge from excel
            excel_file = self.block_config.get(CONFIG_KEY_KNOWLEDGE_FILE)
            if not excel_file:
                abort_during_building(
                    f"Neither knowledge file nor google sheet info is not specified for the block {self.name}.")
            utterances_df, slots_df, entities_df, dictionary_df \
                = self.get_dfs_from_excel(excel_file, utterances_sheet, slots_sheet, entities_sheet, dictionary_sheet)

        function_modules: List[ModuleType] = []  # dictionary function modules
        function_definitions: str = self.block_config.get("function_definitions")  # module name(s) in config
        if function_definitions:
            for function_definition in function_definitions.split(':'):
                function_definition_module: str = function_definition.strip()
                function_modules.append(importlib.import_module(function_definition_module))  # developer specified

        sudachi_normalization: bool = False
        # setting Japanese tokenizer
        if self._language == 'ja':
            sudachi_normalization = self.block_config.get(CONFIG_KEY_SUDACHI_NORMALIZATION, False)
            self._tokenizer = SudachiTokenizer(normalize=sudachi_normalization)


        # convert nlu knowledge dataframes to JSON in SNIPS format
        nlu_knowledge_json = convert_nlu_knowledge(utterances_df, slots_df, entities_df, dictionary_df,
                                                   flags_to_use, function_modules, self.config, self.block_config,
                                                   language=self._language,
                                                   sudachi_normalization=sudachi_normalization)
        # write training file 訓練データファイルを書き出す
        with open(os.path.join(self.config_dir, "_training_data.json"), "w", encoding='utf-8') as fp:
            fp.write(json.dumps(nlu_knowledge_json, indent=2, ensure_ascii=False))
        if self._language == 'en':
            self._nlu_engine = SnipsNLUEngine(config=CONFIG_EN, random_state=SNIPS_SEED)
        elif self._language == 'ja':
            self._nlu_engine = SnipsNLUEngine(config=CONFIG_JA, random_state=SNIPS_SEED)
        self._nlu_engine.fit(nlu_knowledge_json)  # train NLU model

    def get_dfs_from_gs(self, google_sheet_config: Dict[str, str],
                        utterances_sheet: str, slots_sheet: str,
                        entities_sheet: str, dictionary_sheet: str) \
            -> Tuple[DataFrame, DataFrame, DataFrame, DataFrame]:
        """
        Get DataFrames for each sheet in knowledge in google sheets
        Google sheetに書かれた知識からDataframeを取得する。
        :param google_sheet_config: configuration for accessing google sheet
        :param utterances_sheet: utterances sheet name
        :param slots_sheet: slots sheet name
        :param entities_sheet: entities sheet name
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
        entities_data = workbook.worksheet(entities_sheet).get_all_values()
        dictionary_data = workbook.worksheet(dictionary_sheet).get_all_values()
        return pd.DataFrame(utterances_data[1:], columns=utterances_data[0]), \
               pd.DataFrame(slots_data[1:], columns=slots_data[0]), \
               pd.DataFrame(entities_data[1:], columns=entities_data[0]), \
               pd.DataFrame(dictionary_data[1:], columns=dictionary_data[0])

    def get_dfs_from_excel(self, excel_file: str, utterances_sheet: str, slots_sheet: str,
                           entities_sheet: str, dictionary_sheet: str):

        """
        Get DataFrames for each sheet in knowledge in Excel
        Excelに書かれた知識からDataframeを取得する。
        :param excel_file: knowledge file excel
        :param utterances_sheet: utterances sheet name
        :param slots_sheet: slots sheet name
        :param entities_sheet: entities sheet name
        :param dictionary_sheet: dictionary sheet name
        :return: (utterances dataframe, slots dataframe, entities dataframe, dictionary dataframe)
        """

        excel_file_path = os.path.join(self.config_dir, excel_file)
        print(f"reading excel file: {excel_file_path}", file=sys.stderr)
        try:
            df_all: Dict[str, DataFrame] = pd.read_excel(excel_file_path, sheet_name=None)  # read all sheets
        except Exception as e:
            abort_during_building(f"failed to read excel file: {excel_file_path}. {str(e)}")
        # reading slots sheet
        return df_all.get(utterances_sheet), df_all.get(slots_sheet), \
               df_all.get(entities_sheet), df_all.get(dictionary_sheet)

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

        sentence = input[KEY_INPUT_TEXT]
        if sentence == "":
            if self._num_candidates == 1:  # non n-best mode
                nlu_result: Dict[str, Any] = {"type": "", "slots": {}}
            else:  # n-best mode
                nlu_result: List[Dict[str, Any]] = [{"type": "", "slots": {}}]
        else:
            input_to_nlu: str = sentence
            if self._language == 'ja':
                tokens: List[Token] = self._tokenizer.tokenize(sentence)
                input_to_nlu = " ".join([token.form for token in tokens])
            if self._num_candidates == 1:  # non n-best mode
                snips_result: Dict[str, Any] = self._nlu_engine.parse(input_to_nlu)
                nlu_result: Dict[str, Any] = self.one_snips_result_to_nlu_result(snips_result)
            else:  # n-best mode
                snips_results: List[Dict[str, Any]] = self._nlu_engine.parse(input_to_nlu, top_n=self._num_candidates)
                nlu_result: List[Dict[str, Any]] = [self.one_snips_result_to_nlu_result(snips_result)
                                                    for snips_result in snips_results]
        output = {KEY_NLU_RESULT: nlu_result}
        self.log_debug("output: " + str(output), session_id=session_id)

        return output

    def one_snips_result_to_nlu_result(self, snips_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        get nlu result in dialbb format from one snips nlu result
        SNIPSの言語理解結果からDialBBフォーマットの言語理解結果を得る
        :param snips_result: snips nlu result (one result when n-best results are obtained)
        :return: nlu result in DialBB format: {"type": "...", "slots":, {...}}
        """
        intent = snips_result["intent"]["intentName"]
        if intent is None:
            intent = "failure"
        slots = {}
        for snips_slot in snips_result["slots"]:
            if type(snips_slot["value"]) == dict:
                slots[snips_slot["slotName"]] \
                    = self._snips_slot_value_to_dialbb_slot_value(snips_slot["value"]["value"])
            else:
                slots[snips_slot["slotName"]] \
                    = self._snips_slot_value_to_dialbb_slot_value(snips_slot["value"])
        nlu_result = {"type": intent, "slots": slots}
        return nlu_result

    def _snips_slot_value_to_dialbb_slot_value(self, value: str) -> str:
        if self._language == 'ja':
            result = value.replace(' ', '')  # 辞書にないスロット値はスペースを含んでいる場合がある
        else:
            result = value
        return result
