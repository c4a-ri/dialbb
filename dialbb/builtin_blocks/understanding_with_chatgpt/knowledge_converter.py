#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# knowledge_converter.py
#   convert nlu knowledge to be used in the prompt
#   言語理解知識をプロンプトで使う形式に変換する

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

ETC_STR = {"ja": "など", "en": " etc."}
INPUT_STR = {"ja": "入力", "en": "input"}
OUTPUT_STR = {"ja": "出力", "en": "output"}


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
                          block_config: Dict[str, Any], language='ja') -> Tuple[str, str, str, Dict[str, List[str]]]:

    """
    converts nlu knowledge to parts of prompt
    言語理解知識をプロンプトの素材に変換する
    :param utterances_df: utterances sheet dataframe
    :param slots_df: slots sheet dataframe
    :param block_config: block configuration
    :param language: language of this app ('en' or 'ja')
    :return: list of types for prompt, slot definitions for prompt, examples for prompt,
             dict from entities synonym list
    """

    slot_names2entities: Dict[str, List[str]] = {}
    entities2synonyms: Dict[str, List[str]] = {}
    types2utterances: Dict[str, List[str]] = {}
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

    # read utterances sheet
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
            if not types2utterances.get(utterance_type):
                types2utterances[utterance_type] = []
            types2utterances[utterance_type].append(utterance)

            slots: Dict[str, str] = {}
            slots_cell: str = row[COLUMN_SLOTS].strip()
            if slots_cell:
                slots_str: List[str] = [x.strip() for x in re.split('[,，、]', slots_cell)]
                for slot_str in slots_str:
                    pair: List[str] = [x.strip() for x in re.split('[=＝]', slot_str)]
                    if len(pair) != 2:
                        abort_during_building("illegal slot description: " + str(slots_str))
                    slots[pair[0]] = pair[1]  # name -> value
            understanding_results = {"type": utterance_type, "slots": slots}
            utterances2understanding_results[utterance] = understanding_results

    types_in_prompt: str = ""
    for utterance_type in types2utterances.keys():
        types_in_prompt += f"- {utterance_type}\n"

    slot_definitions_in_prompt: str = ""
    for slot_name in slot_names2entities.keys():
        entities: List[str] = slot_names2entities[slot_name]
        slot_definitions_in_prompt += f"- {slot_name}: {', '.join(entities)}, {ETC_STR[language]}\n"

    examples_in_prompt: str = ""
    for utterance, understanding_results in utterances2understanding_results.items():
        examples_in_prompt += f"- {INPUT_STR[language]}: {utterance}\n"
        examples_in_prompt += f"  {OUTPUT_STR[language]}: {str(understanding_results)}\n\n"

    return types_in_prompt, slot_definitions_in_prompt, examples_in_prompt, entities2synonyms


