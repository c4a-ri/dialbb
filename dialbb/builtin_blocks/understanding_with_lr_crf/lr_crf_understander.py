#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# lr_crf_understander.py
#   understand input text using LR and CRF

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import pandas as pd
from pandas import DataFrame

from dialbb.abstract_block import AbstractBlock
from dialbb.builtin_blocks.understanding_with_lr_crf.crf_slot_extractor import CRFSlotExtractor
from dialbb.builtin_blocks.understanding_with_lr_crf.knowledge_converter import convert_nlu_knowledge
from dialbb.builtin_blocks.understanding_with_lr_crf.japanese_pos_tagger import JapanesePosTagger
from dialbb.builtin_blocks.understanding_with_lr_crf.english_pos_tagger import EnglishPosTagger
from dialbb.builtin_blocks.understanding_with_lr_crf.lr_type_estimator import LRTypeEstimator
from dialbb.main import CONFIG_KEY_LANGUAGE
from typing import Any, Dict, List, Tuple, Union
import os
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials


from dialbb.main import ANY_FLAG, KEY_SESSION_ID
from dialbb.util.error_handlers import abort_during_building


CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET: str = "knowledge_google_sheet"  # google sheet info
CONFIG_KEY_SHEET_ID: str = "sheet_id"  # google sheet id
CONFIG_KEY_KEY_FILE: str = "key_file"  # key file for Google sheets API
CONFIG_KEY_KNOWLEDGE_FILE: str = "knowledge_file"  # excel file path
CONFIG_KEY_UTTERANCE_SHEET: str = "utterances_sheet"
CONFIG_KEY_SLOTS_SHEET: str = "slots_sheet"
CONFIG_KEY_PROMPT_TEMPLATE: str = "prompt_template"
CONFIG_KEY_GPT_MODEL: str = "gpt_model"
CONFIG_KEY_NUM_CANDIDATES: str = "num_candidates"

KEY_NLU_RESULT: str = "nlu_result"
KEY_INPUT_TEXT: str = "input_text"

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']


class Understander(AbstractBlock):
    """
    LR and CRF based understander
    """

    def __init__(self, *args):

        super().__init__(*args)


        # sheets in spreadsheet
        utterances_sheet = self.block_config.get(CONFIG_KEY_UTTERANCE_SHEET, "utterances")
        slots_sheet = self.block_config.get(CONFIG_KEY_SLOTS_SHEET, "slots")

        # language: "en" or "ja"
        self._language = self.config.get(CONFIG_KEY_LANGUAGE, 'en')
        if self._language == 'en':
            self._pos_tagger = EnglishPosTagger()
        elif self._language == 'ja':
            self._pos_tagger = JapanesePosTagger()
        else:
            abort_during_building("unsupported language: " + self._language)

        self._num_candidates = self.block_config.get(CONFIG_KEY_NUM_CANDIDATES, 1)
        if type(self._num_candidates) != int or self._num_candidates < 1:
            abort_during_building(f"value of {CONFIG_KEY_NUM_CANDIDATES} must be a natural number.")

        google_sheet_config: Dict[str, str] = self.block_config.get(CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET)
        if google_sheet_config:  # get knowledge from google sheet
            utterances_df, slots_df = self._get_dfs_from_gs(google_sheet_config, utterances_sheet, slots_sheet)
        else:  # get knowledge from excel
            excel_file = self.block_config.get(CONFIG_KEY_KNOWLEDGE_FILE)
            if not excel_file:
                abort_during_building(
                    f"Neither knowledge file nor google sheet info is not specified for the block {self.name}.")
            utterances_df, slots_df = self._get_dfs_from_excel(excel_file, utterances_sheet, slots_sheet)

        # convert nlu knowledge to type and slot definitions
        training_data, self.entities2synonyms, self._slot_ids2slot_names\
            = convert_nlu_knowledge(utterances_df, slots_df, self.block_config, language=self._language)

        self.log_debug(f"{len(training_data)} samples are used for training.")

        for sample in training_data:
            sample['tokens_with_pos'] = self._tokenize_and_tag(sample['example'])  # [(token, pos), (token, pos), ...]

        self._slots_exist: bool = True if self._slot_ids2slot_names else False

        if self._slots_exist:
            self._slot_extractor = CRFSlotExtractor(training_data, language=self._language)  # create crf model
            self.log_debug("CRF model is trained.")
        else:
            self.log_debug("No slots found in the training data. Slots will not be estimated.")

        self._type_estimator = LRTypeEstimator(training_data)   # create lr model
        self.log_debug("LR model is trained.")


    def _get_dfs_from_gs(self, google_sheet_config: Dict[str, str],
                         utterances_sheet: str, slots_sheet: str) -> Tuple[DataFrame, DataFrame]:
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
        understand input sentence using LR and CRF. when num_candidates in config is more than 1,
        n-best results are returned
        LRとCRFを用いて言語理解を行う
        コンフィギュレーションのnum_candidatesが2以上なら、n-bestの言語理解結果が返される
        :param input: e.g. {"input_text": "I love egg salad sandwiches"}
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

        input_text = input[KEY_INPUT_TEXT]
        if not input_text:  # if input is empty
            if self._num_candidates == 1:  # non n-best mode
                nlu_result: Dict[str, Any] = {"type": "", "slots": {}}
            else:  # n-best mode
                nlu_result: List[Dict[str, Any]] = [{"type": "", "slots": {}}]
        else:
            if self._num_candidates == 1:  # non n-best mode
                nlu_result: Dict[str, Any] = self._understand_with_lr_crf(input_text)
            else:  # n-best mode
                nlu_result: List[Dict[str, Any]] = self._understand_with_lr_crf(input_text, top_n=self._num_candidates)

        output = {KEY_NLU_RESULT: nlu_result}
        self.log_debug("output: " + str(output), session_id=session_id)

        return output

    def _get_entity(self, expression: str) -> str:
        """
        return entity if expression is its synonym, otherwise expression as is
        :param expression:
        :return: entity or expression
        """

        for entity in self.entities2synonyms.keys():
            if expression in self.entities2synonyms[entity]:
                return entity
        return expression

    def _understand_with_lr_crf(self, input_text: str, top_n: int=1) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        understand input text using chatgpt
        :param input_text: input text string
        :param top_n: number of candidates
        :return:
        """

        tokens_with_pos: List[Tuple[str, str]] = self._tokenize_and_tag(input_text)  # [(word, pos), (word, pos) ...]
        if self._slots_exist:
            slots_with_ids: Dict[str, str] = self._slot_extractor.extract_slots(tokens_with_pos)
            # change to slot names
            slots = {self._slot_ids2slot_names[slot_id]: value for slot_id, value in slots_with_ids.items()}
            self.log_debug("estracted slots: " + str(slots))
        else:
            slots: Dict[str, str] = {}
        utterance_types, prob_distribution = self._type_estimator.estimate_type(tokens_with_pos)
        self.log_debug("estimated types: " + str(utterance_types))
        self.log_debug("estimated type probabilities: " + str(prob_distribution))

        if top_n == 1:
            return {"type": utterance_types[0], "slots": slots}
        else:  # top n candidates
            if len(utterance_types) > top_n:
                utterance_types = utterance_types[:top_n]
            return [{"type": t, "slots": slots} for t in utterance_types]

    def _tokenize_and_tag(self, input_text: str) -> List[Tuple[str, str]]:
        """
        tokenize input and tag POS labels
        :param input_text: input text
        :return: [(word, pos), (word pos) ...]
        """

        result: List[Tuple[str, str]] = self._pos_tagger.tag(input_text)
        return result
























