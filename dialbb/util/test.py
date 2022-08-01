#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test.py
#   automatically testing app

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


import argparse
from typing import Dict, Any
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from dialbb.main import DialogueProcessor

USER_ID = "user1"

if __name__ == '__main__':

    # read arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="config yaml file")
    parser.add_argument("inputs", help="test input json file")
    args = parser.parse_args()

    with open(args.inputs, encoding='utf-8') as file:
        test_inputs: Dict[str, Any] = json.load(file)

    config_file:str = args.config
    dialogue_processor = DialogueProcessor(config_file)

    for test_utterances in test_inputs.get('test_inputs', []):
        request = {"user_id": USER_ID}
        print("request: " + str(request))
        result = dialogue_processor.process(request, initial=True)
        print("response: " + str(result))
        print("SYS> " + result['system_utterance'])
        session_id = result['session_id']
        for input_utterance in test_utterances.get("user_utterances", []):
            print("USR> " + input_utterance)
            request = {"user_id": USER_ID, "session_id": session_id,
                       "user_utterance": input_utterance}
            print("request: " + str(request))
            result = dialogue_processor.process(request, initial=False)
            print("response: " + str(result))
            print("SYS> " + result['system_utterance'])
            if result['final']:
                break
