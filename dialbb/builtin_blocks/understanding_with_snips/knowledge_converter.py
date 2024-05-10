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

from re import Pattern

from dialbb.builtin_blocks.preprocess.abstract_canonicalizer import AbstractCanonicalizer
from dialbb.builtin_blocks.tokenization.abstract_tokenizer import AbstractTokenizer
from dialbb.util.builtin_block_utils import create_block_object
from dialbb.util.error_handlers import abort_during_building, warn_during_building
from dialbb.main import ANY_FLAG
from dialbb.builtin_blocks.tokenization.abstract_tokenizer import TokenWithIndices

COLUMN_FLAG: str = "flag"
COLUMN_TYPE: str = "type"
COLUMN_UTTERANCE: str = "utterance"
COLUMN_SLOT_NAME: str = "slot name"
COLUMN_ENTITY_CLASS: str = "entity class"
COLUMN_USE_SYNONYMS: str = "use synonyms"
COLUMN_AUTOMATICALLY_EXTENSIBLE: str = "automatically extensible"
COLUMN_MATCHING_STRICTNESS: str = "matching strictness"
COLUMN_ENTITY: str = "entity"
COLUMN_SYNONYMS: str = "synonyms"
KEY_CLASS: str = "class"
KEY_CANONICALIZER: str = "canonicalizer"
KEY_TOKENIZER: str = "tokenizer"
KEY_TOKENS_WITH_INDICES: str = "tokens_with_indices"

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
                          language='ja') -> Dict[str, Any]:
    """
    converts nlu knowledge into SNIPS training data
    言語理解知識をSNIPSの訓練データに変換する
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

    # canonicalizer
    canonicalizer_config: Dict[str, Any] = block_config.get(KEY_CANONICALIZER)
    if not canonicalizer_config:
        abort_during_building("Canonicalizer is not specified in the config of SNIPS understander.")
    canonicalizer: AbstractCanonicalizer = create_block_object(canonicalizer_config)

    tokenizer_config: Dict[str, Any] = block_config.get(KEY_TOKENIZER)
    if not tokenizer_config:
        abort_during_building("Tokenizer is not specified in the config of SNIPS understander.")
    tokenizer: AbstractTokenizer = create_block_object(tokenizer_config)

    snips_intent_definitions: Dict[str, Any] = {}
    snips_entity_definitions: Dict[str, Any] = {}

    slot_names2entity_classes: Dict[str, str] = {}  # from slots sheet

    # when there is no slot sheet
    # slot sheetがない時
    if slots_df is None:  # no slots sheet
        print(f"Warning: no slots sheet. Dummy entity definition is used instead.")
    else:
        # converting slots dataframe
        # slots dataframeの変換
        slots_df.fillna('', inplace=True)
        check_columns([COLUMN_FLAG, COLUMN_SLOT_NAME, COLUMN_ENTITY_CLASS], slots_df, "slots")
        for index, row in slots_df.iterrows():
            if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                continue
            slot: str = row[COLUMN_SLOT_NAME].strip()
            entity_class: str = row[COLUMN_ENTITY_CLASS].strip()
            if not entity_class.startswith("dialbb/"):  # dictionary function
                slot_names2entity_classes[slot] = entity_class
            else:  # entity defined by a dictionary function
                function_name: str = entity_class.replace("dialbb/", "")
                entity_class = function_name  # entity and function name is the same
                slot_names2entity_classes[slot] = entity_class
                function_found = False
                for function_module in function_modules:
                    function = getattr(function_module, function_name, None)
                    function_found = True
                    if function:
                        dictionary: List[Dict[str, Union[str, List[str]]]] \
                            = eval("func(config, block_config)", {},  # execute dictionary function
                                   {"func": function, "config": config, "block_config": block_config})
                        snips_entity_definitions[entity_class] = {'data':  []}
                        for entry in dictionary:
                            entity: str = entry['entity']
                            normalized_entity: str = normalize(entity, canonicalizer, tokenizer)
                            normalized_synonyms: List[str] = [normalize(synonym, canonicalizer, tokenizer)
                                                   for synonym in entry.get('synonyms',[])]
                            if entity != normalized_entity:
                                normalized_synonyms.append(normalized_entity)  # normalized entity is used as a synonym
                            snips_entity_definitions[entity_class]['data'].append({"value": normalized_entity,
                                                                                   "synonyms": normalized_synonyms})
                        break
                if not function_found:
                    abort_during_building(f'dictionary function "{function_name}" is not found.')

        # converting entities dataframe
        # entities dataframeの変換
        check_columns([COLUMN_FLAG, COLUMN_ENTITY_CLASS, COLUMN_USE_SYNONYMS,
                       COLUMN_AUTOMATICALLY_EXTENSIBLE, COLUMN_MATCHING_STRICTNESS], entities_df, "entities")
        entity_class_descriptions: Dict[str, Dict[str, Any]] = {}  # <entity: str> -> {"use_synonyms": <bool>,
                                                      #                   "automatically_extensible": <bool>,
                                                      #                   "matching_strictness": <float>}
        if entities_df is None:  # no entities sheet
            print(f"Warning: no entities sheet.")
        else:
            entities_df.fillna('', inplace=True)
            for index, row in entities_df.iterrows():
                entity_class: str = row[COLUMN_ENTITY_CLASS].strip()
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
                if entity_class.startswith("dialbb/"):
                    entity_class = entity_class.replace("dialbb/", "")
                entity_class_descriptions[entity_class] = {"use_synonyms": use_synonyms,
                                        "automatically_extensible": automatically_extensible,
                                        "matching_strictness": matching_strictness}

        # converting dictionary sheet
        # dictionary sheetの変換
        if dictionary_df is None:  # no dictionary sheet
            print(f"Warning: no dictionary sheet.")
        else:
            dictionary_df.fillna('', inplace=True)  # change empty cells to empty strings
            check_columns([COLUMN_FLAG, COLUMN_ENTITY_CLASS, COLUMN_ENTITY, COLUMN_SYNONYMS], dictionary_df, "dictionary")
            for index, row in dictionary_df.iterrows():
                if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                    continue
                synonyms_string: str = row[COLUMN_SYNONYMS]
                normalized_synonyms: List[str] = [normalize(synonym.strip(), canonicalizer, tokenizer, language)
                                                  for synonym in
                                                  re.split('[,，、]', synonyms_string)]  # convert synonym cell to a list
                entity_class: str = row[COLUMN_ENTITY_CLASS].strip()
                entity: str = row[COLUMN_ENTITY]
                normalized_entity: str = normalize(entity, canonicalizer, tokenizer, language)  # dictionary entry
                if entity != normalized_entity:
                    normalized_synonyms.append(normalized_entity)  # normalized entity is used as a synonym
                if entity_class in snips_entity_definitions.keys():
                    snips_entity_definitions[entity_class]['data'].append({"value": normalized_entity,
                                                                           "synonyms": normalized_synonyms})
                else:
                    snips_entity_definitions[entity_class] = {'data': [{"value": normalized_entity,
                                                                        "synonyms": normalized_synonyms}]}

        # integrate information in entities dataframe into dictionary
        # entities dataframeの情報を辞書と統合する
        for entity_class in snips_entity_definitions.keys():
            entity_definition = snips_entity_definitions[entity_class]
            if entity_class in entity_class_descriptions.keys():
                entity_definition['use_synonyms'] = entity_class_descriptions[entity_class]['use_synonyms']
                entity_definition['automatically_extensible'] = entity_class_descriptions[entity_class]['automatically_extensible']
                entity_definition['matching_strictness'] = entity_class_descriptions[entity_class]['matching_strictness']
            else:
                print(f"Error: entity '{entity_class}' in the dictionary sheet is not in the entity sheet.", file=sys.stderr)
                sys.exit(1)

        # add entity in the slot sheet but not in the dictionary sheet to the dictionary
        for slot in slot_names2entity_classes.keys():
            entity_class = slot_names2entity_classes[slot]
            if entity_class not in snips_entity_definitions:
                snips_entity_definitions[entity_class] = {}

    if snips_entity_definitions == {}:  # if no slots & entity information is provided
        snips_entity_definitions = {"city": {"data": [{"value": "london"}],  # dummy is needed for SNIPS
                                             "use_synonyms": True,
                                             "automatically_extensible": True,
                                             "matching_strictness": 1.0}}

    # convert utterances sheet
    # utterances sheetの変換
    intents2utterances: Dict[str, List[str]] = {}

    utterances_df.fillna('', inplace=True)
    for index, row in utterances_df.iterrows():
        if row[COLUMN_FLAG].strip() not in flags and ANY_FLAG not in flags:
            continue
        intent: str = row[COLUMN_TYPE]
        if intent in intents2utterances.keys():
            intents2utterances[intent].append(row[COLUMN_UTTERANCE].strip())
        else:
            intents2utterances[intent] = [row[COLUMN_UTTERANCE].strip()]

    # create intent definitions
    for intent in intents2utterances.keys():
        utterance_descs: List[Dict[str, Any]] = []  # [{"data": [...]}, {"data": [...]}, ...]
        for utterance in intents2utterances[intent]:
            if language == "en":
                utterance_fragments = get_utterance_fragments_en(utterance, canonicalizer, tokenizer,
                                                                 slot_names2entity_classes)
            elif language == "ja":
                utterance_fragments = get_utterance_fragments_ja(utterance, canonicalizer, tokenizer,
                                                                 slot_names2entity_classes)
            if utterance_fragments:  # ignore if this is None
                utterance_desc: Dict[str, Any] = {'data': utterance_fragments}
                utterance_descs.append(utterance_desc)
        snips_intent_definitions[intent] = {'utterances': utterance_descs}

    result = {"intents": snips_intent_definitions, "entities": snips_entity_definitions, "language": language}
    return result


def get_utterance_fragments_en(utterance: str, canonicalizer: AbstractCanonicalizer,
                               tokenizer: AbstractTokenizer,
                               slot2entity: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    divides slot parts and other parts of the input utterance string (English)
    入力発話文字列のスロット部分とそうでない部分を分ける (英語)
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


def get_utterance_fragments_ja(utterance: str, canonicalizer: AbstractCanonicalizer,
                               tokenizer: AbstractTokenizer,
                               slot2entity: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    divides slot parts and other parts of the input utterance string (Japanese)
    入力発話文字列のスロット部分とそうでない部分を分ける （日本語）
    :param utterance: input utterance string
    :param canonicalizer: canonicalizer object
    :param tokenizer: tokenizer object
    :param slot2entity: mapping from slots to entities
    :return: list of fragments or empty list if an error occurs
    """

    fragments: List[Dict[str, Any]] = []
    utterance:str = canonicalize_tagged_utterance_ja(utterance, canonicalizer)
    utterance_without_tags: str = tagged_utterance_pattern.sub(r'\1',utterance)
    input_to_tokenizer_block: Dict[str, str] = {"input_text": utterance_without_tags}
    output_from_tokenizer_block: Dict[str, Any] = tokenizer.process(input_to_tokenizer_block)  # tokenization
    tokens_with_indices: List[TokenWithIndices] = output_from_tokenizer_block.get(KEY_TOKENS_WITH_INDICES, {})
    # if DEBUG:
    #     print("utterance_with_tags: " + utterance)
    #     print("utterance_without_tags: " + utterance_without_tags)
    #     print("tokenized: " + " ".join([token.form for token in tokens]))
    end_index2token: Dict[int, TokenWithIndices] = {}  # {3: <token end at 3>, 6: <token end at 6> ...}
    for token in tokens_with_indices:
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


def canonicalize_tagged_utterance_en(input_text: str, canonicalizer: AbstractCanonicalizer) -> str:
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


def canonicalize_tagged_utterance_ja(input_text: str, canonicalizer: AbstractCanonicalizer) -> str:
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


def normalize(input_text: str, canonicalizer: AbstractCanonicalizer,
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
