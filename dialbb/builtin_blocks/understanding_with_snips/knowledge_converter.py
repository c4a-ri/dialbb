#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# knowledge_converter.py
#   convert nlu knowledge to SNIPS training data format
#   言語理解知識をSNIPSの訓練データ形式に変換する

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from types import ModuleType
from typing import Dict, List, Any, Union
import sys
import re
from pandas import DataFrame

from dialbb.builtin_blocks.util.abstract_tokenizer import AbstractTokenizer
from dialbb.builtin_blocks.util.canonicalizer import Canonicalizer
from re import Pattern

from dialbb.builtin_blocks.util.sudachi_tokenizer import SudachiTokenizer, Token
from dialbb.util.error_handlers import abort_during_building, warn_during_building
from dialbb.main import ANY_FLAG

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


def convert_nlu_knowledge(utterances_df: DataFrame, slots_df: DataFrame, entities_df: DataFrame,
                          dictionary_df: DataFrame, flags: List[str], function_modules: List[ModuleType],
                          config: Dict[str, Any], block_config: Dict[str, Any],
                          language='en') -> Dict[str, Any]:
    """
    converts nlu knowledge into SNIPS training data
    :param utterances_df: utterances sheet dataframe
    :param slots_df: slots sheet dataframe
    :param entities_df: entities sheet dataframe
    :param dictionary_df: dictionary sheet dataframe
    :param flags: list of flags to use
    :param function_modules: list of dictionary function modules
    :param config: application configuration
    :param block_config: block configuration
    :param language: language of this app ('en' or 'ja')
    :return: SNIPS training data (to be saved as a JSON file)
    """

    print(f"converting nlu knowledge.")

    canonicalizer = Canonicalizer(language)
    tokenizer = None
    if language == 'ja':
        tokenizer = SudachiTokenizer()

    intent_definitions: Dict[str, Any] = {}
    entity_definitions: Dict[str, Any] = {}
    slot2entity: Dict[str, str] = {}  # from slots sheet

    # when there is no slot sheet
    if slots_df is None:  # no slots sheet
        print(f"Warning: no slots sheet. Dummy entity definition is used instead.")
    else:
        slots_df.fillna('', inplace=True)
        check_columns([COLUMN_FLAG, COLUMN_SLOT, COLUMN_ENTITY], slots_df, "slots")
        for index, row in slots_df.iterrows():
            if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                continue
            slot: str = row[COLUMN_SLOT].strip()
            entity: str = row[COLUMN_ENTITY].strip()
            if not entity.startswith("dialbb/"):  # dictionary function
                slot2entity[slot] = entity
            else:  # entity defined by a dictionary function
                function_name: str = entity.replace("dialbb/", "")
                entity: str = function_name  # entity and function name is the same
                slot2entity[slot] = entity
                function_found = False
                for function_module in function_modules:
                    function = getattr(function_module, function_name, None)
                    function_found = True
                    if function:
                        dictionary: List[Dict[str, Union[str, List[str]]]] \
                            = eval("func(config, block_config)", {}, # execute dictionary function
                                   {"func": function, "config": config, "block_config": block_config})
                        entity_definitions[entity] = {'data':  []}
                        for entry in dictionary:
                            normalized_value = normalize(entry['value'], canonicalizer, tokenizer)
                            normalized_synonyms = [normalize(synonym, canonicalizer, tokenizer)
                                                   for synonym in entry.get('synonyms',[])]
                            entity_definitions[entity]['data'].append({"value": normalized_value,
                                                                       "synonyms": normalized_synonyms})
                        break
                if not function_found:
                    abort_during_building(f'dictionary function "{function_name}" is not found.')

        # reading entities sheet
        check_columns([COLUMN_FLAG, COLUMN_ENTITY, COLUMN_USE_SYNONYMS,
                       COLUMN_AUTOMATICALLY_EXTENSIBLE, COLUMN_MATCHING_STRICTNESS], entities_df, "entities")
        entity_descs: Dict[str, Dict[str, Any]] = {}  # <entity: str> -> {"use_synonyms": <bool>,
                                                      #                   "automatically_extensible": <bool>,
                                                      #                   "matching_strictness": <float>}
        if entities_df is None:  # no entities sheet
            print(f"Warning: no entities sheet.")
        else:
            entities_df.fillna('', inplace=True)
            for index, row in entities_df.iterrows():
                entity: str = row[COLUMN_ENTITY].strip()
                if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                    continue
                if row[COLUMN_USE_SYNONYMS].strip() == "yes":
                    use_synonyms: bool = True
                else:
                    use_synonyms = False
                if row[COLUMN_AUTOMATICALLY_EXTENSIBLE].strip() == "yes":
                    automatically_extensible: bool = True
                else:
                    automatically_extensible = False
                matching_strictness = row[COLUMN_MATCHING_STRICTNESS]
                try:
                    matching_strictness = float(matching_strictness)
                except Exception as e:
                    abort_during_building(f"matching strictness must be a number: {str(matching_strictness)}")
                if entity.startswith("dialbb/"):
                    entity = entity.replace("dialbb/", "")
                entity_descs[entity] = {"use_synonyms": use_synonyms,
                                        "automatically_extensible": automatically_extensible,
                                        "matching_strictness": matching_strictness}

        # reading dictionary sheet
        if dictionary_df is None:  # no dictionary sheet
            print(f"Warning: no dictionary sheet.")
        else:
            dictionary_df.fillna('', inplace=True)  # change empty cells to empty strings
            check_columns([COLUMN_FLAG, COLUMN_ENTITY, COLUMN_VALUE, COLUMN_SYNONYMS], dictionary_df, "dictionary")
            for index, row in dictionary_df.iterrows():
                if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                    continue
                synonyms_string: str = row[COLUMN_SYNONYMS]
                normalized_synonyms: List[str] = [normalize(synonym.strip(), canonicalizer, tokenizer, language)
                                                  for synonym in
                                                  re.split('[,，、]', synonyms_string)]  # convert synonym cell to a list
                entity = row[COLUMN_ENTITY].strip()
                normalized_value: str = normalize(row['value'], canonicalizer, tokenizer, language)  # dictionary entry
                if entity in entity_definitions.keys():
                    entity_definitions[entity]['data'].append({"value": normalized_value,
                                                               "synonyms": normalized_synonyms})
                else:
                    entity_definitions[entity] = {'data': [{"value": normalized_value,
                                                            "synonyms": normalized_synonyms}]}

        # integrate information in entity sheet into dictionary
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

    if entity_definitions == {}:  # if no slots & entity information is provided
        entity_definitions = {"city": {"data": [{"value": "london"}],  # dummy is needed for SNIPS
                                       "use_synonyms": True,
                                       "automatically_extensible": True,
                                       "matching_strictness": 1.0}}

    # read utterances sheet
    intent2utterances: Dict[str, List[str]] = {}

    utterances_df.fillna('', inplace=True)
    for index, row in utterances_df.iterrows():
        if row[COLUMN_FLAG].strip() not in flags and ANY_FLAG not in flags:
            continue
        intent: str = row[COLUMN_TYPE]
        if intent in intent2utterances.keys():
            intent2utterances[intent].append(row[COLUMN_UTTERANCE].strip())
        else:
            intent2utterances[intent] = [row[COLUMN_UTTERANCE].strip()]

    # create intent definitions
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


def get_utterance_fragments_en(utterance: str, canonicalizer: Canonicalizer,
                            tokenizer: AbstractTokenizer,
                            slot2entity: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    divides slot parts and other parts of the input utterance string
    入力発話文字列のスロット部分とそうでない部分を分ける
    :param utterance: input utterance string
    :param canonicalizer: canonicalizer object
    :param tokenizer: tokenizer object
    :param slot2entity: mapping from slots to entities
    :return: list of fragments or empty list if an error occurs
    """
    fragments: List[Dict[str, Any]] = []
    utterance = canonicalize_tagged_utterance_en(utterance, canonicalizer)
    index: int = 0
    for m in tagged_utterance_pattern.finditer(utterance):  # regular expression matching
        if m.start() > index:
            fragments.append({"text": utterance[index:m.start()]})  # non-slot part
        slot_name = m.group(2)
        entity = slot2entity.get(slot_name)
        if entity is None:
            warn_during_building(f"Error: slot {slot_name} is not defined in the slot sheet.")
            return []
        fragments.append({"text": m.group(1), "slot_name": slot_name, "entity": entity})
        index = m.end()
    if index < len(utterance):
        fragments.append({"text": utterance[index:]})  # from the last slot to the end of sentence
    return fragments


def get_utterance_fragments_ja(utterance: str, canonicalizer: Canonicalizer,
                            tokenizer: AbstractTokenizer,
                            slot2entity: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    divides slot parts and other parts of the input utterance string
    入力発話文字列のスロット部分とそうでない部分を分ける
    :param utterance: input utterance string
    :param canonicalizer: canonicalizer object
    :param tokenizer: tokenizer object
    :param slot2entity: mapping from slots to entities
    :return: list of fragments or empty list if an error occurs
    """

    fragments: List[Dict[str, Any]] = []
    utterance:str = canonicalize_tagged_utterance_ja(utterance, canonicalizer)
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
        if utterance[i] == '(':
            if in_token:
                print(f"slot tag boundaries and token boundaries do not match near '{utterance[i+1]}':" + utterance)
                return []
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
            if slot_name not in slot2entity:
                warn_during_building(f"slot '{slot_name}' is not defined in the entities sheet.")
                return None
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


def canonicalize_tagged_utterance_en(input_text: str, canonicalizer: Canonicalizer) -> str:
    """
    canonicalizes English utterance with slot tags
    :param input_text: utterance string with slot tags
    :param canonicalizer: canonicalizer object
    :return: canonicalized utterance string with slot tags
    """
    # add spaces before and after slots
    result: str = re.sub(r"\(", " (", input_text)
    result = re.sub("]", "] ", result)
    result = canonicalizer.canonicalize(result)
    return result


def canonicalize_tagged_utterance_ja(input_text: str, canonicalizer: Canonicalizer) -> str:
    """
    canonicalizes Japanese utterance with slot tags
    :param input_text: utterance string with slot tags
    :param canonicalizer: canonicalizer object
    :return: canonicalized utterance string with slot tags
    """
    # delete spaces before and after slots
    result: str = re.sub(r"\s+\(", "(", input_text)
    result: str = re.sub(r"\)\s+", ")", input_text)
    result = re.sub("]\s+", "]", result)
    result = re.sub("\s+\[", "[", result)
    result = canonicalizer.canonicalize(result)
    return result


def normalize(input_text: str, canonicalizer: Canonicalizer,
              tokenizer: AbstractTokenizer, language: str = "ja") -> str:
    """
    canonicalizes and tokenizes input string
    :param input_text: input string
    :param canonicalizer: Canonicalizer object
    :param tokenizer: Tokenizer object
    :param language: language ('ja' or 'en')
    :return: canonicalized and tokenized input string
    """

    if language == "en":
        return canonicalizer.canonicalize(input_text)
    elif language == "ja":
        return " ".join(token.form for token in tokenizer.tokenize(canonicalizer.canonicalize(input_text)))
