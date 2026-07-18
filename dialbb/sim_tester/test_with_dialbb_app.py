#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 C4A Research Institute, Inc.
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
#
# test_with_dialbb_app.py
#   Perform test with dialbb application
#   DialBB アプリケーションを利用したシミュレーションによるテストの実行

import json
import os

from dialbb.main import DialogueProcessor
import traceback
from collections.abc import Generator


USER_ID: str = "user1"
DEFAULT_MAX_TURNS: int = 15


def test_with_dialbb(
        test_config: dict[str, object],
        test_config_dir: str,
        app_to_test: DialogueProcessor,
        output_file: str | None = None,
        json_output: bool = False) -> Generator[str, None, None]:
    """
    test using LLM-based simulator
    :param test_config: config for test
    :param test_config_dir: directory of for test config file
    :param app_to_test: DialBB app to test
    :param output_file: file to output log
    :param json_output: if True, output file will be JSON
    :return: list of logs in JSON format
    """

    max_turns: int = test_config.get('max_turns', DEFAULT_MAX_TURNS)

    # setting output file
    out_fp = None
    if output_file and not json_output:
        out_fp = open(output_file, mode='w', encoding='utf-8')

    results = []  # results in JSON

    for simulator_config in test_config.get("configs"):
        simulator_config_file = os.path.join(test_config_dir, simulator_config)

        result = test_one_simulator_config(
            app_to_test,
            simulator_config_file,
            max_turns,
            out_fp
        )

        try:
            # Sequentially retrieve data from a generator
            while True:
                yield next(result)
        except StopIteration as e:
            # Retrieve JSON results in bulk
            results.append(e.value)

    if out_fp:
        out_fp.close()

    if output_file and json_output:  # JSON mode
        with open(output_file, mode='w', encoding='utf-8') as fp:
            json.dump(results, fp, indent=2, ensure_ascii=False)

def test_one_simulator_config(
    app_to_test: DialogueProcessor,
    simulator_config_file: str,
    max_turns: int,
    out_fp,
) -> Generator[str, None, dict[str, object]]:
    result = {}

    simulator_app = DialogueProcessor(simulator_config_file)

    log_text = ""

    num_turns: int = 0

    # first turn

    result['dialogue'] = []

    sim_res = simulator_app.process({"user_id": USER_ID}, initial=True)
    aux_data = sim_res.get("aux_data", {})
    sim_session_id = sim_res['session_id']

    request_to_app = {"user_id": USER_ID, "aux_data": aux_data}  # initial request
    log_text += "----settings\n"
    log_text += "---\n"
    log_text += "----init\n"
    log_text += f"aux data: {str(aux_data)}\n"

    response = app_to_test.process(request_to_app, initial=True)
    print("response: " + str(response))
    system_utterance: str = response['system_utterance']
    print("SYS> " + system_utterance)
    result['dialogue'].append({"speaker": "system", "utterance": system_utterance})
    log_text += f"System: {system_utterance}\n"
    yield log_text
    session_id = response['session_id']

    while True:
        request_to_simulator: dict[str, object] = {
            "user_utterance": system_utterance,
            "session_id": sim_session_id,
            "user_id": USER_ID,
            "aux_id": response.get("aux_id", {})
        }
        simulator_res: dict[str, object] = simulator_app.process(request_to_simulator)
        sim_user_utterance: str = simulator_res.get("system_utterance", "")
        result['dialogue'].append({"speaker": "user", "utterance": sim_user_utterance})
        log_text += f"User: {sim_user_utterance}\n"
        yield f"User: {sim_user_utterance}\n"
        num_turns += 1
        print("USR> " + sim_user_utterance)
        request = {
            "user_id": USER_ID,
            "session_id": session_id,
            "user_utterance": sim_user_utterance,
            "aux_data": simulator_res.get("aux_data", {})
        }
        print("request: " + str(request))
        response = app_to_test.process(request, initial=False)
        print("response: " + str(response))
        system_utterance = response['system_utterance']
        print("SYS> " + system_utterance)
        result['dialogue'].append({"speaker": "system", "utterance": system_utterance})
        log_text += f"System: {system_utterance}\n"
        yield f"System: {system_utterance}\n"
        if response['final'] or num_turns >= max_turns:
            break

    print(log_text)

    if out_fp:
        print(log_text, file=out_fp)

    return result
