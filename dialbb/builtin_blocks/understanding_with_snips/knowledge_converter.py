#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# knowledge_converter.py
#   convert nlu knowledge to SNIPS training data format

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import pandas as pd
from typing import Dict, List, Any
import sys
import re
from pandas import DataFrame

from dialbb.builtin_blocks.util.abstract_tokenizer import AbstractTokenizer
from dialbb.builtin_blocks.util.canonicalizer import Canonicalizer
from re import Pattern

from dialbb.builtin_blocks.util.sudachi_tokenizer import SudachiTokenizer, Token
from dialbb.util.error_handlers import abort_during_building, warn_during_building
from dialbb.main import ANY_FLAG, DEBUG

COLUMN_FLAG: str = "flag"
COLUMN_TYPE: str = "type"
COLUMN_UTTERANCE: str = "utterance"
COLUMN_SLOT: str = "slot"
COLUMN_ENTITY: str = "entity"
COLUMN_USE_SYNONYMS: str = "use synonyms"
COLUMN_AUTOMATICALLY_EXTENSIBLE: str = "automatically extensible"
COLUMN_MATCHING_STRICTNESS: str = "matching strictness"
COLUMN_VALUE: str = "value"
COLUMN_SYNONYMS: str = "synonyms"

tagged_utterance_pattern: Pattern = re.compile(r"\(([^)]+)\)\s*\[([^]]+)]")


def check_columns(required_columns: List[str], df: DataFrame, sheet: str) -> bool:
    """
    check if required columns exit in the sheet of the dataframe
    """
    columns = df.columns.values.tolist()
    for required_column in required_columns:
        if required_column not in columns:
            print(f"Column '{required_column}' is missing in sheet '{sheet}'. "
                  + "There might be extra whitespaces.", file=sys.stderr)
            sys.exit(1)
    return True


def convert_nlu_knowledge(spreadsheet_file: str, utterances_sheet: str,
                          slots_sheet: str, entities_sheet: str,
                          dictionary_sheet: str, flags: List[str],
                          language='en') -> Dict[str, Any]:
    """
    convert nlu knowledge in the spread sheet into snips knowledge format
    :param spreadsheet_file:
    :param utterances_sheet:
    :param slots_sheet:
    :param entities_sheet:
    :param dictionary_sheet:
    :param flags:
    :param language:
    :return: SNIPS format (in Jason)
    """

    print(f"converting nlu knowledge.")

    canonicalizer = Canonicalizer(language)
    tokenizer = None
    if language == 'ja':
        tokenizer = SudachiTokenizer()

    intent_definitions: Dict[str, Any] = {}
    entity_definitions: Dict[str, Any] = {}
    slot2entity: Dict[str, str] = {}  # from slots sheet

    print(f"reading spreadsheet: {spreadsheet_file}", file=sys.stderr)
    try:
        df_all: Dict[str, DataFrame] = pd.read_excel(spreadsheet_file, sheet_name=None)  # 全てのシートを読み込む
    except Exception as e:
        abort_during_building(f"failed to read spreadsheet: {spreadsheet_file}. {str(e)}")

    # reading slots sheet
    slots_df = df_all.get(slots_sheet)

    # when there is no slot sheet
    if slots_df is None:  # no slots sheet
        warn_during_building(f"Warning: no slots sheet '{slots_sheet}'. Dummy entity definition is used instead.")
        entity_definitions = {"city": {"data": [{"value": "london"}],
                                       "use_synonyms": True,
                                       "automatically_extensible": True,
                                       "matching_strictness": 1.0}}
    else:
        check_columns([COLUMN_FLAG, COLUMN_SLOT, COLUMN_ENTITY], slots_df, slots_sheet)
        for index, row in slots_df.iterrows():
            if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                continue
            slot = row[COLUMN_SLOT]
            slot2entity[slot] = row[COLUMN_ENTITY]

        # reading entities sheet
        entities_df = df_all.get(entities_sheet)
        if entities_df is None:
            print(f"no entities sheet '{entities_sheet}'", file=sys.stderr)
            sys.exit(1)
        check_columns([COLUMN_FLAG, COLUMN_ENTITY, COLUMN_USE_SYNONYMS,
                       COLUMN_AUTOMATICALLY_EXTENSIBLE, COLUMN_MATCHING_STRICTNESS], entities_df, entities_sheet)
        entity_descs: Dict[str, Dict[str, Any]] = {}  # <entity: str> -> {"use_synonyms": <bool>,
                                                      #                   "automatically_extensible": <bool>,
                                                      #                   "matching_strictness": <float>}
        for index, row in entities_df.iterrows():
            entity: str = row[COLUMN_ENTITY]
            if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                continue
            if row[COLUMN_USE_SYNONYMS] == "yes":
                use_synonyms: bool = True
            else:
                use_synonyms = False
            if row[COLUMN_AUTOMATICALLY_EXTENSIBLE] == "yes":
                automatically_extensible: bool = True
            else:
                automatically_extensible = False
            matching_strictness = row[COLUMN_MATCHING_STRICTNESS]
            if type(matching_strictness) not in [float, int]:
                print(f"matching strictness must be a number: {str(matching_strictness)}", file=sys.stderr)
                sys.exit(1)
            entity_descs[entity] = {"use_synonyms": use_synonyms,
                                                "automatically_extensible": automatically_extensible,
                                                "matching_strictness": matching_strictness}

        # reading dictionary sheet
        dictionary_df: DataFrame = df_all.get(dictionary_sheet)
        if dictionary_df is None:
            print(f"no dictionary sheet '{dictionary_sheet}'", file=sys.stderr)
            sys.exit(1)
        dictionary_df.fillna('', inplace=True)  # change empty cells to empty strings
        check_columns([COLUMN_FLAG, COLUMN_ENTITY, COLUMN_VALUE, COLUMN_SYNONYMS], dictionary_df, dictionary_sheet)
        for index, row in dictionary_df.iterrows():
            if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                continue
            synonyms_string: str = row[COLUMN_SYNONYMS]
            normalized_synonyms: List[str] = [normalize(synonym.strip(), canonicalizer, language)
                                              for synonym in
                                              re.split('[,，、]', synonyms_string)]  # convert synonym cell to a list
            entity = row[COLUMN_ENTITY]
            normalized_value: str = normalize(row['value'], canonicalizer, language)  # dictionary entry
            if entity in entity_definitions.keys():
                entity_definitions[entity]['data'].append({"value": normalized_value, "synonyms": normalized_synonyms})
            else:
                entity_definitions[entity] = {'data': [{"value": normalized_value, "synonyms": normalized_synonyms}]}

        # integrate information in entity sheetの into dictionary
        for entity in entity_definitions.keys():
            entity_definition = entity_definitions[entity]
            if entity in entity_descs.keys():
                entity_definition['use_synonyms'] = entity_descs[entity]['use_synonyms']
                entity_definition['automatically_extensible'] = entity_descs[entity]['automatically_extensible']
                entity_definition['matching_strictness'] = entity_descs[entity]['matching_strictness']
            else:
                print(f"Error: entity '{entity}' in the dictionary sheet is not in the entity sheet.", file=sys.stderr)
                sys.exit(1)

        # add entity in the slot sheet but not in the dictionary sheet to the dictionary
        for slot in slot2entity.keys():
            entity = slot2entity[slot]
            if entity not in entity_definitions:
                entity_definitions[entity] = {}

    # read utterances sheet
    utterances_df: DataFrame = df_all.get(utterances_sheet)
    if utterances_df is None:
        print(f"no utterance sheet: {utterances_sheet}.", file=sys.stderr)
        sys.exit(1)
    intent2utterances: Dict[str, List[str]] = {}
    for index, row in utterances_df.iterrows():
        intent: str = row['type']
        if intent in intent2utterances.keys():
            intent2utterances[intent].append(row['utterance'])
        else:
            intent2utterances[intent] = [row['utterance']]

    for intent in intent2utterances.keys():
        utterance_descs: List[Dict[str, Any]] = []  # [{"data": [...]}, {"data": [...]}, ...]
        for utterance in intent2utterances[intent]:
            if language == "en":
                utterance_fragments = get_utterance_fragments_en(utterance, canonicalizer, tokenizer, slot2entity)
            elif language == "ja":
                utterance_fragments = get_utterance_fragments_ja(utterance, canonicalizer, tokenizer, slot2entity)
            if utterance_fragments:  # ignore if this is None
                utterance_desc: Dict[str, Any] = {'data': utterance_fragments}
                utterance_descs.append(utterance_desc)
        intent_definitions[intent] = {'utterances': utterance_descs}

    result = {"intents": intent_definitions, "entities": entity_definitions, "language": language}
    return result


# divide slot parts and other parts
def get_utterance_fragments_en(utterance: str, canonicalizer: Canonicalizer,
                            tokenizer: AbstractTokenizer,
                            slot2entity: Dict[str, str], language='en') -> List[Dict[str, Any]]:
    fragments: List[Dict[str, Any]] = []
    utterance = normalize_tagged_utterance_en(utterance, canonicalizer)
    index: int = 0
    for m in tagged_utterance_pattern.finditer(utterance): # regular expression matching
        if m.start() > index:
            fragments.append({"text": utterance[index:m.start()]})  # non slot part
        slot_name = m.group(2)
        entity = slot2entity.get(slot_name)
        if entity is None:
            warn_during_building(f"Error: slot {slot_name} is not defined in the slot sheet.")
        fragments.append({"text": m.group(1), "slot_name": slot_name, "entity": entity})
        index = m.end()
    if index < len(utterance):
        fragments.append({"text": utterance[index:]})  # from the last slot to the end of sentence
    return fragments


def get_utterance_fragments_ja(utterance: str, canonicalizer: Canonicalizer,
                            tokenizer: AbstractTokenizer,
                            slot2entity: Dict[str, str] ) -> List[Dict[str, Any]]:
    fragments: List[Dict[str, Any]] = []
    utterance:str = normalize_tagged_utterance_ja(utterance, canonicalizer)
    utterance_without_tags: str = tagged_utterance_pattern.sub(r'\1',utterance)
    tokens: List[Token] = tokenizer.tokenize(utterance_without_tags)  # tokenization
    # if DEBUG:
    #     print("utterance_with_tags: " + utterance)
    #     print("utterance_without_tags: " + utterance_without_tags)
    #     print("tokenized: " + " ".join([token.form for token in tokens]))
    end_index2token: Dict[int, Token] = {}  # {3: <token end at 3>, 6: <token end at 6> ...}
    for token in tokens:
        end_index2token[token.end-1] = token # -1 is necessary because end index is one bigger than the end position
    slot_tags = [{"start": m.start(), "end": m.end(),
                  "slot_name": m.group(2),"value": m.group(1)}
                 for m in tagged_utterance_pattern.finditer(utterance)]
    slot_tag_index: int = 0
    i: int = 0  # index in utterance_with_tags
    j: int = 0  # index in utterance_without_tags
    fragment_text = ""
    in_slot_name: bool = False
    in_token: bool = False
    while i < len(utterance):
        #print(f"i={str(i)}, j={str(j)}, fragment_text={fragment_text}, fragments={str(fragments)}")
        if utterance[i] == '(':
            if in_token:
                print(f"slot tag boundaries and token boundaries do not match near '{utterance[i+1]}':" + utterance)
                return None
            if fragment_text:
                fragments.append({"text": fragment_text+" "})
                fragment_text = ""
            elif i > 0:
                fragments.append({"text": " "})  # between two slot tags
        elif utterance[i] == ')':
            pass
        elif utterance[i] == '[':
            in_slot_name = True
        elif utterance[i] == ']':
            slot_name: str = slot_tags[slot_tag_index]["slot_name"]
            fragments.append({"text": fragment_text, "slot_name": slot_name, "entity": slot2entity[slot_name]})
            in_slot_name = False
            slot_tag_index += 1
            fragment_text = " "
        elif not in_slot_name:  # character
            token = end_index2token.get(j)
            if token:
                if fragment_text == " ":
                    fragment_text += token.form
                elif fragment_text:
                    fragment_text += " " + token.form
                else:
                    fragment_text = token.form
                in_token = False
            else:
                in_token = True
            j += 1
        i += 1
    if fragment_text != " ":
        fragments.append({"text": fragment_text})
    return fragments


def normalize_tagged_utterance_en(input_text: str, canonicalizer: Canonicalizer) -> str:
    # add spaces before and after slots
    result: str = re.sub(r"\(", " (", input_text)
    result = re.sub("]", "] ", result)
    result = canonicalizer.canonicalize(result)
    return result

def normalize_tagged_utterance_ja(input_text: str, canonicalizer: Canonicalizer) -> str:
    # delete spaces before and after slots
    result: str = re.sub(r"\s+\(", "(", input_text)
    result: str = re.sub(r"\)\s+", ")", input_text)
    result = re.sub("]\s+", "]", result)
    result = re.sub("\s+\[", "[", result)
    result = canonicalizer.canonicalize(result)
    return result


def normalize(input_text: str, canonicalizer: Canonicalizer, tokenizer: AbstractTokenizer, language: str = "en") -> str:
    if language == "en":
        return canonicalizer.canonicalize(input_text)
    elif language == "ja":
        return " ".join(token.form for token in tokenizer.tokenize(canonicalizer.canonicalize(input_text)))
