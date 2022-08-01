#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# snips_understander.py
#   understand input text using snips nlu

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from dialbb.builtin_blocks.understanding_with_snips.knowledge_converter import convert_nlu_knowledge
from dialbb.abstract_block import AbstractBlock
from dialbb.main import CONFIG_KEY_FLAGS_TO_USE, CONFIG_KEY_LANGUAGE
from typing import Any, Dict, List
import os
import json

from snips_nlu import SnipsNLUEngine
from snips_nlu.default_configs import CONFIG_EN, CONFIG_JA

from dialbb.main import ANY_FLAG, KEY_SESSION_ID
from dialbb.util.error_handlers import abort_during_building
from dialbb.builtin_blocks.util.sudachi_tokenizer import SudachiTokenizer, Token

SNIPS_SEED = 42  # from SNIPS tutorial

CONFIG_KEY_KNOWLEDGE_FILE: str = "knowledge_file"
CONFIG_KEY_UTTERANCE_SHEET: str = "utterances_sheet"
CONFIG_KEY_SLOTS_SHEET: str = "slots_sheet"
CONFIG_KEY_ENTITIES_SHEET: str = "entities_sheet"
CONFIG_KEY_DICTIONARY_SHEET: str = "dictionary_sheet"
KEY_INPUT_TEXT: str = "input_text"
KEY_NLU_RESULT: str = "nlu_result"

class Understander(AbstractBlock):
    """
    SNIPS based understander
    """

    def __init__(self, *args):

        super().__init__(*args)

        spreadsheet = self.block_config.get(CONFIG_KEY_KNOWLEDGE_FILE)
        flags_to_use = self.block_config.get(CONFIG_KEY_FLAGS_TO_USE, [ANY_FLAG])
        if not spreadsheet:
            abort_during_building(f"knowledge_file is not specified for the block {self.name}.")
        spreadsheet = os.path.join(self.config_dir, spreadsheet)
        utterances_sheet = self.block_config.get(CONFIG_KEY_UTTERANCE_SHEET, "utterances")
        slots_sheet = self.block_config.get(CONFIG_KEY_SLOTS_SHEET, "slots")
        entities_sheet = self.block_config.get(CONFIG_KEY_ENTITIES_SHEET, "entities")
        dictionary_sheet = self.block_config.get(CONFIG_KEY_DICTIONARY_SHEET, "dictionary")
        self._language = self.config[CONFIG_KEY_LANGUAGE]
        nlu_knowledge_json = convert_nlu_knowledge(spreadsheet, utterances_sheet, slots_sheet,
                                                   entities_sheet, dictionary_sheet,
                                                   flags_to_use, language=self._language)
        # training fileを書き出す
        with open(os.path.join(self.config_dir, "_training_data.json"), "w", encoding='utf-8') as fp:
            fp.write(json.dumps(nlu_knowledge_json, indent=2, ensure_ascii=False))
        if self._language == 'en':
            self._nlu_engine = SnipsNLUEngine(config=CONFIG_EN, random_state=SNIPS_SEED)
        elif self._language == 'ja':
            self._nlu_engine = SnipsNLUEngine(config=CONFIG_JA, random_state=SNIPS_SEED)
            self._tokenizer = SudachiTokenizer()
        self._nlu_engine.fit(nlu_knowledge_json)

    def process(self, input: Dict[str, Any], initial=False) -> Dict[str, Any]:
        """
        understand input sentenc usig SNIPS
        :param e.g. {"sentence": "I love egg salad sandwiches"}
        :param initial: whether processing the first utterance of the session
        :return: e.g., {"nlu_result {"type": "tell_favorite_sandwiches", "slots": {"sandwich": "egg salad sandwich"}}}
        """

        session_id: str = input.get(KEY_SESSION_ID, "undecided")
        self.log_debug("input: " + str(input), session_id=session_id)

        if initial:
            intent = ""
            slots: Dict[str, str] = {}
        else:
            sentence = input[KEY_INPUT_TEXT]
            input_to_nlu: str = sentence
            if self._language == 'ja':
                tokens: List[Token] = self._tokenizer.tokenize(sentence)
                input_to_nlu = " ".join([token.form for token in tokens])
            snips_result = self._nlu_engine.parse(input_to_nlu)
            intent = snips_result["intent"]["intentName"]
            if intent is None:
                intent = "failure"
            slots = {}
            for snips_slot in snips_result["slots"]:
                if type(snips_slot["value"]) == dict:
                    slots[snips_slot["slotName"]] \
                        = self._snip_slot_value_to_dialbb_slot_value(snips_slot["value"]["value"])
                else:
                    slots[snips_slot["slotName"]] \
                        = self._snip_slot_value_to_dialbb_slot_value(snips_slot["value"])

        nlu_result = {"type": intent, "slots": slots}
        output = {KEY_NLU_RESULT: nlu_result}
        self.log_debug("output: " + str(output), session_id=session_id)

        return output

    def _snip_slot_value_to_dialbb_slot_value(self, value: str) -> str:
        if self._language == 'ja':
            result = value.replace(r'\s', '')  # TODO use expressions in the excel file
        else:
            result = value
        return result