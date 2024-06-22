#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# knowledge_converter.py
#   convert nlu knowledge to be used in LR and CRF training
#   言語理解知識をLRとCRFの訓練データ形式に変換する。

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, List, Any, Union, Tuple
import sys
import re
from pandas import DataFrame

from dialbb.builtin_blocks.preprocess.abstract_canonicalizer import AbstractCanonicalizer
from dialbb.util.builtin_block_utils import create_block_object
from dialbb.util.error_handlers import abort_during_building, warn_during_building
from dialbb.main import ANY_FLAG
from dialbb.main import CONFIG_KEY_FLAGS_TO_USE

COLUMN_FLAG: str = "flag"
COLUMN_TYPE: str = "type"
COLUMN_UTTERANCE: str = "utterance"
COLUMN_SLOT_NAME: str = "slot name"
COLUMN_ENTITY: str = "entity"
COLUMN_SYNONYMS: str = "synonyms"
COLUMN_SLOTS: str = "slots"

KEY_CLASS: str = "class"
KEY_CANONICALIZER: str = "canonicalizer"

def check_columns(required_columns: List[str], df: DataFrame, sheet: str) -> bool:
    """
    checks if required columns exit in the sheet of the dataframe
    DataFrameに必須のカラムがあるか調べる
    :param required_columns: list of required column names
    :param df: DataFrame
    :param sheet: sheet name to be used in error messages
    :return: True if the check passes
    """

    columns = df.columns.values.tolist()
    for required_column in required_columns:
        if required_column not in columns:
            abort_during_building(f"Column '{required_column}' is missing in sheet '{sheet}'. "
                                  + "There might be extra whitespaces.")
    return True


def convert_nlu_knowledge(utterances_df: DataFrame, slots_df: DataFrame,
                          block_config: Dict[str, Any],
                          language='ja') -> Tuple[List[Dict[str, Any]], Dict[str, List[str]], Dict[str, str]]:

    """
    converts nlu knowledge to parts of prompt
    言語理解知識をプロンプトの素材に変換する
    :param utterances_df: utterances sheet dataframe
    :param slots_df: slots sheet dataframe
    :param block_config: block configuration
    :param language: language of this app ('en' or 'ja')
    :return: Tuple of the folowing:
             - list of training data, each of which is a dict having keys 'type', 'example, and 'slots'
               e.g., {"type": "ask-weather",
                      "example": "tell me the weather in new york tomorrow",
                      "slots": {"place": "new york", "date": "tomorrow"}}
             - dict from entities to synonym lists
             - dict from slot id's to slot names
    """

    slot_names2entities: Dict[str, List[str]] = {}
    entities2synonyms: Dict[str, List[str]] = {}
    utterances2understanding_results: Dict[str, Dict[str, Any]] = {}

    print(f"converting nlu knowledge.")

    # which rows to use
    flags: List[str] = block_config.get(CONFIG_KEY_FLAGS_TO_USE, [ANY_FLAG])

    # canonicalizer
    canonicalizer_config: Dict[str, Any] = block_config.get(KEY_CANONICALIZER)
    if not canonicalizer_config:
        abort_during_building("Canonicalizer is not specified in the config of SNIPS understander.")
    canonicalizer: AbstractCanonicalizer = create_block_object(canonicalizer_config)

    # when there is no slot sheet
    # slot sheetがない時
    if slots_df is None:  # no slots sheet
        abort_during_building(f"Warning: no slots sheet.")
    else:
        # converting slots dataframe
        # slots dataframeの変換
        slots_df.fillna('', inplace=True)
        check_columns([COLUMN_FLAG, COLUMN_SLOT_NAME, COLUMN_ENTITY, COLUMN_SYNONYMS], slots_df, "slots")
        for index, row in slots_df.iterrows():
            if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                continue
            slot_name: str = row[COLUMN_SLOT_NAME].strip()
            entity: str = row[COLUMN_ENTITY].strip()
            entity = canonicalizer.canonicalize(entity)
            if not slot_names2entities.get(slot_name):
                slot_names2entities[slot_name] = []
            slot_names2entities[slot_name].append(entity)

            synonyms: List[str] = [canonicalizer.canonicalize(x.strip())
                                   for x in re.split('[,，、]', row[COLUMN_SYNONYMS])]  # split synonym cell
            entities2synonyms[entity] = synonyms

    training_data: List[Dict[str, Any]] = []
    # read utterances sheet

    slot_ids2slot_names: Dict[str, str] = {}
    j: int = 0

    if utterances_df is None:  # no utterance sheet
        abort_during_building(f"Warning: no utterances sheet.")
    else:
        utterances_df.fillna('', inplace=True)
        check_columns([COLUMN_FLAG, COLUMN_TYPE, COLUMN_UTTERANCE, COLUMN_SLOTS], utterances_df, "utterances")
        for index, row in utterances_df.iterrows():
            if row[COLUMN_FLAG].strip() not in flags and ANY_FLAG not in flags:
                continue
            utterance_type: str = row[COLUMN_TYPE].strip()
            utterance: str = row[COLUMN_UTTERANCE].strip()
            slots: Dict[str, str] = {}
            slots_cell: str = row[COLUMN_SLOTS].strip()
            if slots_cell:
                slots_str: List[str] = [x.strip() for x in re.split('[,，、]', slots_cell)]
                for slot_str in slots_str:
                    pair: List[str] = [canonicalizer.canonicalize(x.strip()) for x in re.split('[=＝]', slot_str)]
                    if len(pair) != 2:
                        abort_during_building("illegal slot description: " + str(slots_str))
                    slot_id = None
                    for id, name in slot_ids2slot_names.items():
                        if name == pair[0]:
                            slot_id = id
                            break
                    if slot_id is None:   # new slot
                        slot_id = "SLOT-" + str(j)  # slot id is SLOT-0, SLOT-1, ...
                        j += 1
                    slot_ids2slot_names[slot_id] = pair[0]
                    slots[slot_id] = pair[1]  # name -> value
            training_sample: Dict[str, Any] = {"type": utterance_type, "slots": slots, "example": utterance}
            training_data.append(training_sample)

    return training_data, entities2synonyms, slot_ids2slot_names


