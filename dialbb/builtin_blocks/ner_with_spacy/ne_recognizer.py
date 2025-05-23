#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024-2025 C4A Research Institute, Inc.
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
# spacey_nlp.py
# ne_recognizer.py
#   recognizer named entities using spaCy/GiNZA

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from dialbb.abstract_block import AbstractBlock
from typing import List, Any, Dict, Tuple
import spacy
from dialbb.util.error_handlers import abort_during_building


class SpaCyNER(AbstractBlock):

    def __init__(self, *args):
        super().__init__(*args)

        self.check_io_config(inputs=["input_text", "aux_data"], outputs=['aux_data'])
        spacy_model: str = self.block_config.get('model')
        try:
            self.nlp: spacy.Language = spacy.load(spacy_model)
        except Exception as e:
            abort_during_building("can't load spacy model: " + spacy_model)
        ruler = self.nlp.add_pipe('entity_ruler', config={'overwrite_ents': True})
        patterns: List[Dict[str, str]] = self.block_config.get("patterns")
        if patterns:
            ruler.add_patterns(patterns)

    def process(self, input: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """

        :param input. keys: "input_text", "input_aux_data"
        :return: output. keyss: "output_text", "output_aux_data"
        """
        aux_data: Dict[str, Any] = input['aux_data']
        if not aux_data:
            aux_data = {}
        self.log_debug("input: " + str(input), session_id=session_id)
        doc: spacy.Language = self.nlp(input['input_text'])
        self.log_debug(f"text:{doc.text}", session_id=session_id)
        ner_result = {}

        # get entities and labels
        for ent in doc.ents:
            if ent.label_ in ner_result.keys():
                ner_result[ent.label_].add(ent.text)
            else:
                # use set to avoid duplication
                ner_result[ent.label_] = {ent.text}

        for label, entities in ner_result.items():
            key: str = "NE_" + label
            entities: str = ':'.join(entities)  # {"NE_Person": "Joe Biden:Kamala Harris", ...}
            aux_data[key] = entities
            self.log_debug(f"NEs {entities} in the class {key} is found.", session_id=session_id)

        output: Dict[str, Any] = {"aux_data": aux_data}
        self.log_debug("output: " + str(output))
        return output
