#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test.py
#   automatically testing app
#   自動テスト用スクリプト

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
    parser.add_argument("inputs", help="test input json file")  # test input file
    parser.add_argument("--output", help="output json file", required=False)  # output file (same format with test file)
    args = parser.parse_args()

    with open(args.inputs, encoding='utf-8') as file:
        test_inputs: Dict[str, Any] = json.load(file)

    config_file: str = args.config
    dialogue_processor = DialogueProcessor(config_file)

    log_lines = []
    # reads each user utterance from test input file and processes it
    for test_utterances in test_inputs.get('test_inputs', []):
        log_lines.append("----init")
        request = {"user_id": USER_ID}
        print("request: " + str(request))
        result = dialogue_processor.process(request, initial=True)
        print("response: " + str(result))
        print("SYS> " + result['system_utterance'])
        log_lines.append("System: " + result['system_utterance'])
        session_id = result['session_id']
        for input_utterance in test_utterances.get("user_utterances", []):
            print("USR> " + input_utterance)
            log_lines.append("User: " + input_utterance)
            request = {"user_id": USER_ID, "session_id": session_id,
                       "user_utterance": input_utterance}
            print("request: " + str(request))
            result = dialogue_processor.process(request, initial=False)
            print("response: " + str(result))
            print("SYS> " + result['system_utterance'])
            log_lines.append("System: " + result['system_utterance'])
            if result['final']:
                break

    if args.output:
        with open(args.output, mode='w', encoding='utf-8') as fp:
            for log_line in log_lines:
                print(log_line, file=fp)


