#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# chatgpt.py
#   performs dialogue using ChatGPT
#   ChatGPTを用いた対話

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import os
import sys
import traceback
from typing import Dict, Any, List, Union, Tuple
import openai
from dialbb.abstract_block import AbstractBlock
from dialbb.util.error_handlers import abort_during_building

DEFAULT_GPT_MODEL: str = "gpt-3.5-turbo"


class ChatGPT(AbstractBlock):
    """
    performs dialogue using ChatGPT
    """

    def __init__(self, *args):

        super().__init__(*args)

        openai_key: str = os.environ.get('OPENAI_KEY', "")
        if not openai_key:
            abort_during_building("OPENAI_KEY is not defined")
        self._openai_client = openai.OpenAI(api_key=openai_key)
        self._gpt_model = self.block_config.get("gpt_model", DEFAULT_GPT_MODEL)

        # read prefix and postfix
        self._prompt_prefix: str = self.block_config.get("prompt_prefix", "")
        self._prompt_postfix: str = self.block_config.get("prompt_postfix", "")

        if self._prompt_prefix.startswith('@'):
            self._prompt_prefix = self.read_from_file(self._prompt_prefix[1:])
        if self._prompt_postfix.startswith('@'):
            self._prompt_postfix = self.read_from_file(self._prompt_postfix[1:])

        self._final_phrase = self.block_config.get("final_phrase", "")

        # {"sessoin1" : [{"speaker": "user", "utterance": <user utterance>},
        #                {"speaker": "system", "utterance": <system utterance>},
        #                ....]
        # ...}
        self._dialogue_history: Dict[str, List[Dict[str, str]]] = {}

    def read_from_file(self, filename: str) -> str:
        """
        read a text file into a string
        :param filename: file name path (relative path from the configuration file)
        :return: read string
        """

        filepath: str = os.path.join(self.config_dir, filename)
        with open(filepath, encoding='utf-8') as fp:
            result: str = fp.read()
        return result

    def process(self, input_data: Dict[str, Any], session_id: str) -> Union[Dict[str, Union[dict, Any]], str]:
        """
        main process of this block

        :param input_data: input to the block. The keys are "user_utterance" (str), "user_id" (str), and "aux_data" (dict)
        :param session_id: session id string
        :return: output from the block. The keys are "system utterance" (str), "aux_data" (dict), and "final" (bool).
        """

        self._user_id = input_data["user_id"]
        if session_id not in self._dialogue_history.keys():  # first turn
            self._dialogue_history[session_id] = []
            system_utterance = self.block_config.get("first_system_utterance")
            aux_data = input_data['aux_data']
            final = False
        else:  # second turn and after
            self._dialogue_history[session_id].append({"speaker": "user", "utterance": input_data["user_utterance"]})
            system_utterance, aux_data, final \
                = self.generate_system_utterance(self._dialogue_history[session_id],
                                                 session_id,
                                                 self._user_id,
                                                 input_data["aux_data"])
        self._dialogue_history[session_id].append({"speaker": "system", "utterance": system_utterance})
        if self._final_phrase and self._final_phrase in system_utterance:   # final phrase appear in system utterance
            final = True
        return {"system_utterance": system_utterance,
                "aux_data": aux_data,
                "final": final}

    def _generate_with_openai_gpt(self, prompt: str) -> str:

        """
        Generates system utterance using openai GPT. Does not use "assistant" role.
        This is to be used in the "generate_system_utterance" method.

        :param prompt: prompt string
        :return: generated string
        """

        chat_completion = None
        while True:
            try:
                chat_completion = self._openai_client.with_options(timeout=10).chat.completions.create(
                    model=self._gpt_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    )
            except openai.APITimeoutError:
                continue
            except Exception as e:
                self.log_error("OpenAI Error: " + traceback.format_exc())
                sys.exit(1)
            finally:
                if not chat_completion:
                    continue
                else:
                    break
        system_utterance: str = chat_completion.choices[0].message.content
        return system_utterance

    def generate_system_utterance(self, dialogue_history: List[Dict[str, str]],
                                  session_id: str,
                                  user_id: str,
                                  aux_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any], bool]:

        """
        Generates system utterance. This method is to be implemented in a child class.

        :param dialogue_history: list of turn information  [{"speaker": "system", "utterance": <system utterance>}
                                                            {"speaker": "user", "utterance": <user utterance>} ...]
        :param session_id: user id string
        :param user_id: user id string
        :param aux_data: auxiliary data received from main
        :return: a tuple of system utterance string, update aux_data, and final flag
        """

        raise NotImplementedError

