#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 C4A Research Institute, Inc.
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
# knowledge_converter.py
#   convert DST knowledge to be used in the prompt

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import json
import re
from typing import Any, Dict, List, Tuple

from pandas import DataFrame

from dialbb.main import ANY_FLAG, CONFIG_KEY_FLAGS_TO_USE
from dialbb.util.error_handlers import abort_during_building


COLUMN_FLAG: str = "flag"
COLUMN_DIALOGUE: str = "dialogue"
COLUMN_SLOT_NAME: str = "slot name"
COLUMN_ENTITY: str = "entity"

COLUMN_SYNONYMS: str = "synonyms"
COLUMN_SLOTS: str = "slots"

ETC_STR = {"ja": "など", "en": "etc."}
INPUT_STR = {"ja": "入力", "en": "Input"}
OUTPUT_STR = {"ja": "出力", "en": "Output"}


def check_columns(required_columns: List[str], df: DataFrame, sheet: str) -> bool:
    columns = df.columns.values.tolist()
    for required_column in required_columns:
        if required_column not in columns:
            abort_during_building(f"Column '{required_column}' is missing in sheet '{sheet}'. "
                                  + "There might be extra whitespaces.")
    return True


def convert_dst_knowledge(
        dialogues_df: DataFrame,
        slots_df: DataFrame,
        block_config: Dict[str, Any],
        language: str = 'ja') -> Tuple[str, str, Dict[str, List[str]]]:
    slot_names2entities: Dict[str, List[str]] = {}
    entities2synonyms: Dict[str, List[str]] = {}
    dialogues2dst_results: Dict[str, Dict[str, str]] = {}
    flags: List[str] = block_config.get(CONFIG_KEY_FLAGS_TO_USE, [ANY_FLAG])

    if slots_df is None:
        abort_during_building("Warning: no slots sheet.")
    slots_df.fillna('', inplace=True)
    slots_df = slots_df.map(lambda x: x.strip() if isinstance(x, str) else x)
    check_columns([COLUMN_FLAG, COLUMN_SLOT_NAME, COLUMN_ENTITY, COLUMN_SYNONYMS], slots_df, "slots")
    for _, row in slots_df.iterrows():
        if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
            continue
        slot_name = row[COLUMN_SLOT_NAME].strip()
        entity = _normalize_text(row[COLUMN_ENTITY])
        slot_names2entities.setdefault(slot_name, []).append(entity)
        synonyms = [_normalize_text(value) for value in re.split('[,，、]', row[COLUMN_SYNONYMS]) if value.strip()]
        entities2synonyms[entity] = synonyms

    if dialogues_df is None:
        abort_during_building("Warning: no dialogues sheet.")
    dialogues_df.fillna('', inplace=True)
    check_columns([COLUMN_FLAG, COLUMN_DIALOGUE, COLUMN_SLOTS], dialogues_df, "dialogues")
    for _, row in dialogues_df.iterrows():
        if row[COLUMN_FLAG].strip() not in flags and ANY_FLAG not in flags:
            continue
        dialogue = row[COLUMN_DIALOGUE].strip()
        dialogues2dst_results[dialogue] = _parse_slots_cell(row[COLUMN_SLOTS])

    slot_definitions_in_prompt = ""
    for slot_name, entities in slot_names2entities.items():
        slot_definitions_in_prompt += f"- {slot_name}: {', '.join(entities)}, {ETC_STR[language]}\n"

    examples_in_prompt = ""
    for dialogue, dst_result in dialogues2dst_results.items():
        dialogue_with_indent = dialogue.replace('\n', '\n    ')
        examples_in_prompt += f"- {INPUT_STR[language]}:\n    {dialogue_with_indent}\n"
        examples_in_prompt += f"  {OUTPUT_STR[language]}: {json.dumps(dst_result, ensure_ascii=False)}\n\n"

    return slot_definitions_in_prompt, examples_in_prompt, entities2synonyms


def _parse_slots_cell(slots_cell: str) -> Dict[str, str]:
    slots: Dict[str, str] = {}
    slots_cell = slots_cell.strip()
    if not slots_cell:
        return slots
    slot_strings: List[str] = [value.strip() for value in re.split('[,，、]', slots_cell) if value.strip()]
    for slot_str in slot_strings:
        pair: List[str] = [value.strip() for value in re.split('[=＝]', slot_str)]
        if len(pair) != 2:
            abort_during_building("illegal slot description: " + str(slot_strings))
        slots[pair[0]] = _normalize_text(pair[1])
    return slots


def _normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip()