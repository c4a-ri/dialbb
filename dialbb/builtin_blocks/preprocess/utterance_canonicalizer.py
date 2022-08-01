#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# utterance_canonicalizer.py
#   canonicalization block

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from dialbb.builtin_blocks.util.canonicalizer import Canonicalizer
from dialbb.abstract_block import AbstractBlock
from dialbb.main import CONFIG_KEY_LANGUAGE, KEY_SESSION_ID
from typing import Any, Dict

supported_languages = ("en", "ja")

class UtteranceCanonicalizer(AbstractBlock):

    def __init__(self, *args):
        super().__init__(*args)
        self._language = self.config.get(CONFIG_KEY_LANGUAGE, "en") # default language is english
        if self._language not in supported_languages: # check if language is supported
            self.log_error(f"{self._language} is not a supported language. Supported languages are: "
                              + str(supported_languages))
        self._canonicalizer = Canonicalizer(self._language)

    def process(self, input: Dict[str, Any], initial=False) -> Dict[str, Any]:
        """
        canonicalize input text
        :param input: key: "input_text"
        :return: key: "output_text" (canonicalized text)
        """

        session_id = input.get(KEY_SESSION_ID, "undecided")
        self.log_debug("input: " + str(input), session_id=session_id)
        if initial:
            result = ""
        else:
            result = self._canonicalizer.canonicalize(input['input_text'])
        output = {"output_text": result}
        self.log_debug("output: " + str(output), session_id=session_id)
        return output
