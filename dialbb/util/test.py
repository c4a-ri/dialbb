#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 C4A Research Institute, Inc.
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
# test.py
#   automatically testing app
#   自動テスト用スクリプト

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import argparse
from typing import Dict, Any, List
import sys
import os
from statistics import mean

from dialbb.main import DialogueProcessor

USER_ID = "user1"

if __name__ == '__main__':

    # read arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="config yaml file")
    parser.add_argument("inputs", help="test input file")  # test input file
    parser.add_argument("--output", help="output json file", required=False)  # output file (same format with test file)
    args = parser.parse_args()

    with open(args.inputs, encoding='utf-8') as fp:
        test_input_lines = fp.readlines()

    config_file: str = args.config
    dialogue_processor = DialogueProcessor(config_file)

    log_lines: List[str] = []
    previous_system_utterance: str = ""
    session_id: str = ""
    ignorance_mode: bool = False

    # reads each user utterance from test input file and processes it
    num_uus: List[int] = []
    uu_count: int = 0
    initial: bool = True
    for line in test_input_lines:
        line = line.strip()
        if line == '':
            continue
        elif line.startswith("----"):
            if initial:
                initial = False
            else:
                num_uus.append(uu_count)
                uu_count = 0
                ignorance_mode: bool = False
            print(line)
            log_lines.append(line)
            request = {"user_id": USER_ID}
            print("request: " + str(request))
            result = dialogue_processor.process(request, initial=True)
            print("response: " + str(result))
            print("SYS> " + result['system_utterance'])
            previous_system_utterance = result['system_utterance']
            log_lines.append("System: " + result['system_utterance'])
            session_id = result['session_id']
        elif ignorance_mode:
            continue
        elif line.startswith("User: "):
            user_utterance = line.replace("User: ", "")
            uu_count += 1
            print("USR> " + user_utterance)
            log_lines.append("User: " + user_utterance)
            request = {"user_id": USER_ID, "session_id": session_id,
                       "user_utterance": user_utterance}
            print("request: " + str(request))
            result = dialogue_processor.process(request, initial=False)
            print("response: " + str(result))
            print("SYS> " + result['system_utterance'])
            previous_system_utterance = result['system_utterance']
            log_lines.append("System: " + result['system_utterance'])
            if result['final']:
                ignorance_mode = True
        elif line.startswith("System: "):
            system_utterance = line.replace("System: ", "")
            if system_utterance != previous_system_utterance:
                print("Warning: system utterance does not match test input.")
        else:
            raise Exception("illegal test inputs.")

    num_uus.append(uu_count)

    print("Summary: ")
    print("# of scenarios: " + str(len(num_uus)))
    print("min # of user utterances: " + str(min(num_uus)))
    print("max # of user utterances: " + str(max(num_uus)))
    print("mean # of user utterances: " + str(mean(num_uus)))

    for i, num in enumerate(num_uus):
        print(f"scenario {str(i+1)}: # of user utterances: {str(num)}")

    if args.output:
        with open(args.output, mode='w', encoding='utf-8') as fp:
            for log_line in log_lines:
                print(log_line, file=fp)
        print("Dialogues have been written in the file: " + args.output)


