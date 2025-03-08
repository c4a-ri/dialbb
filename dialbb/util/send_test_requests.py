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
# send_test_requests.py
#   automatically sends test requests
#   自動でリクエストを送る

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Any, List
import argparse
from pprint import pprint
from dialbb.main import DialogueProcessor
import json

USER_ID: str = 'user1'


def main():

    # read arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="config yaml file")
    parser.add_argument("inputs", help="test requests json file")  # test input file
    args = parser.parse_args()

    # read config file
    config_file: str = args.config

    # read input file
    with open(args.inputs, encoding='utf-8') as file:
        all_requests: List[List[Dict[str, Any]]] = json.load(file)

    # create dialogue processor object
    dialogue_processor = DialogueProcessor(config_file)

    all_logs: List[List[Dict[str, Any]]] = []

    for requests in all_requests:
        print("session start.")
        session_log = []
        all_logs.append(session_log)
        session_id = ""
        for request in requests:
            if session_id == "":
                if not request.get('user_id'):
                    request['user_id'] = USER_ID
                print("request: " + str(request))
                session_log.append({"request": request})
                response: Dict[str, Any] = dialogue_processor.process(request, initial=True)
                session_id: str = response['session_id']
            else:
                if not request.get('user_id'):
                    request['user_id'] = USER_ID
                request["session_id"] = session_id
                print("request: " + str(request))
                session_log.append({"request": request})
                response: Dict[str, Any] = dialogue_processor.process(request)
            print("response: " + str(response))
            session_log.append({"response": response})
            if response['final']:
                break

    pprint(all_logs)


if __name__ == '__main__':
    main()
