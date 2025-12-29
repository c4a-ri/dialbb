#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# knowledge_converter.py
#   convert NER knowledge to be used in the prompt
#   固有表現抽出知識をプロンプトで使う形式に変換する

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, List, Any, Tuple
import re
from pandas import DataFrame

from dialbb.util.error_handlers import abort_during_building
from dialbb.main import ANY_FLAG
from dialbb.main import CONFIG_KEY_FLAGS_TO_USE

COLUMN_FLAG: str = "flag"
COLUMN_UTTERANCE: str = "utterance"
COLUMN_ENTITIES: str = "entities"

COLUMN_CLASS: str = "class"
COLUMN_EXPLANATION: str = "explanation"
COLUMN_EXAMPLES: str = "examples"

KEY_CLASS: str = "class"
KEY_ENTITY: str = "entity"
KEY_RESULT: str = "result"

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


def convert_ner_knowledge(utterances_df: DataFrame, classes_df: DataFrame,
                          block_config: Dict[str, Any], language='ja') -> Tuple[str, str, str, str]:

    """
    converts NER knowledge to parts of prompt
    固有表現抽出知識をプロンプトの素材に変換する
    :param utterances_df: utterances sheet dataframe
    :param classes_df: classes sheet dataframe
    :param block_config: block configuration
    :param language: language of this app ('en' or 'ja')
    :return: class list, class explanations, NE examples, and NER result examples to be used in the prompt
    """

    classes2explanations: Dict[str, str] = {}
    classes2examples: Dict[str, List[str]] = {}

    # utterance -> {'result': [(class, ne), (class ne) ...]}
    utterances2ner_results: Dict[str, Dict[str, List[Dict[str, str]]]] = {}

    print(f"converting NER knowledge.")

    # which rows to use
    flags: List[str] = block_config.get(CONFIG_KEY_FLAGS_TO_USE, [ANY_FLAG])


    # when there is no slot sheet
    # slot sheetがない時
    if classes_df is None:  # no slots sheet
        abort_during_building(f"Warning: no classes sheet.")
    else:
        # converting slots dataframe
        # slots dataframeの変換
        classes_df.fillna('', inplace=True)
        classes_df = classes_df.map(lambda x: x.strip() if isinstance(x, str) else x)  # strip
        check_columns([COLUMN_FLAG, COLUMN_CLASS, COLUMN_EXPLANATION, COLUMN_EXAMPLES], classes_df, "classes")
        for index, row in classes_df.iterrows():
            if row[COLUMN_FLAG] not in flags and ANY_FLAG not in flags:
                continue
            class_name: str = row[COLUMN_CLASS].strip()
            explanation: str = row[COLUMN_EXPLANATION].strip()
            classes2explanations[class_name] = explanation

            examples: List[str] = [x.strip()
                                   for x in re.split('[,，、]', row[COLUMN_EXAMPLES])]  # split examples
            classes2examples[explanation] = examples

    # read utterances sheet
    if utterances_df is None:  # no utterance sheet
        abort_during_building(f"Warning: no utterances sheet.")
    else:
        utterances_df.fillna('', inplace=True)
        utterances_df = utterances_df.map(lambda x: x.strip() if isinstance(x, str) else x)  # strip
        check_columns([COLUMN_FLAG, COLUMN_UTTERANCE, COLUMN_ENTITIES], utterances_df, "utterances")
        for index, row in utterances_df.iterrows():
            if row[COLUMN_FLAG].strip() not in flags and ANY_FLAG not in flags:
                continue
            utterance: str = row[COLUMN_UTTERANCE].strip()

            entities: List[Dict[str, str]] = []
            entities_cell: str = row[COLUMN_ENTITIES].strip()
            if entities_cell:
                entities_str: List[str] = [x.strip() for x in re.split('[,，、]', entities_cell)]
                for entity_str in entities_str:
                    pair: List[str] = [x.strip() for x in re.split('[=＝]', entity_str)]
                    if len(pair) != 2:
                        abort_during_building("illegal slot description: " + str(entities_str))
                    entities.append({KEY_CLASS: pair[0], KEY_ENTITY: pair[1]})  # (class. value)
            utterances2ner_results[utterance] = {KEY_RESULT: entities}

    class_list_in_prompt: str = ""
    for class_name in classes2explanations.keys():
        class_list_in_prompt += f"- {class_name}\n"

    explanations_in_prompt: str = ""
    for class_name, explanation in classes2explanations.items():
        explanations_in_prompt += f"- {class_name}: {explanation}\n"

    ne_examples_in_prompt: str = ""
    for class_name, examples in classes2examples.items():
        ne_examples_in_prompt += f"- {class_name}: {', '.join(examples)}{ETC_STR[language]}\n"

    ner_examples_in_prompt: str = ""
    for utterance, ner_results in utterances2ner_results.items():
        ner_examples_in_prompt += f"- {INPUT_STR[language]}: {utterance}\n"
        ner_examples_in_prompt += f"  {OUTPUT_STR[language]}: {str(ner_results)}\n\n"

    return class_list_in_prompt, explanations_in_prompt, ne_examples_in_prompt, ner_examples_in_prompt


