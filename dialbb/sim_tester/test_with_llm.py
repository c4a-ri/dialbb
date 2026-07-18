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
# test_with_llm.py
#   Perform test with LLM-based simulation
#   LLMを利用したシミュレーションによるテストの実行
import json
import os
import sys

from dialbb.main import DialogueProcessor
from dialbb.sim_tester.llm_tester import LLMTester
import traceback
from collections.abc import Generator


USER_ID: str = "user1"
DEFAULT_MAX_TURNS: int = 15
DEFAULT_TEMPERATURE: float = 0.7


def test_with_llm(test_config: dict[str, object],
                  test_config_dir: str,
                  app_to_test: DialogueProcessor,
                  output_file: str | None = None,
                  json_output: bool = False,
                  prompt_params: dict[str, str] | None = None) -> Generator[str, None, None]:
    """
    test using LLM-based simulator
    :param test_config: config for test
    :param test_config_dir: directory of for test config file
    :param app_to_test: DialBB app to test
    :param output_file: file to output log
    :param json_output: if True, output file will be JSON
    :param prompt_params: parameters to replace tags in prompt
    :return: list of logs in JSON format
    """



    # read settings
    settings: list[dict[str, object]] = []
    setting_descriptions: list[dict[str, str]] = test_config.get("settings")
    for setting_description in setting_descriptions:
        prompt_template_file = setting_description.get("prompt_template")
        if not prompt_template_file:
            print("no prompt template file specified.")
            sys.exit(1)
        with open(os.path.join(test_config_dir, prompt_template_file), encoding='utf-8') as fp:
            prompt_template = fp.read()

        if prompt_params:
            for param, value in prompt_params.items():
                prompt_template = prompt_template.replace("{" + param + "}", value)

        initial_aux_data = {}
        initial_aux_data_file: str | None = setting_description.get("initial_aux_data")
        if initial_aux_data_file:
            file: str = os.path.join(test_config_dir, initial_aux_data_file)
            try:
                with open(file, encoding='utf-8') as fp:
                    initial_aux_data: dict[str, object] = json.load(fp)
            except Exception as e:
                print(traceback.format_exc())
                print("problem with reading json file: " + file)
                sys.exit(1)

        settings.append({"prompt_template": prompt_template, "initial_aux_data": initial_aux_data})

    # temperature list
    temperatures: list[float] = test_config.get("temperatures", [DEFAULT_TEMPERATURE])

    user_simulator = LLMTester(test_config)

    max_turns = test_config.get('max_turns', DEFAULT_MAX_TURNS)

    # setting output file
    out_fp = None
    if output_file and not json_output:
        out_fp = open(output_file, mode='w', encoding='utf-8')

    results = []  # results in JSON

    for setting in settings:
        for temperature in temperatures:
            # run test
            result = test_one_setting(
                user_simulator,
                app_to_test,
                setting,
                temperature,
                max_turns,
                out_fp,
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


def test_one_setting(
    user_simulator: LLMTester ,
    app_to_test: DialogueProcessor,
    setting: dict[str, object],
    temperature: float,
    max_turns: int,
    out_fp,
) -> Generator[str, None, dict[str, object]]:
    result = {}

    initial_aux_data: dict[str, object] = setting['initial_aux_data']
    prompt_template: str = setting['prompt_template']
    user_simulator.set_parameters_and_clear_history(prompt_template)

    log_text = ""

    num_turns: int = 0

    # first turn

    result['prompt_template'] = prompt_template
    result['dialogue'] = []
    result['temperature'] = temperature
    result['initial_aux_data'] = initial_aux_data

    request = {"user_id": USER_ID, "aux_data": initial_aux_data}  # initial request
    log_text += "----settings\n"
    log_text += f"model: {user_simulator.get_llm_model()}\n"
    log_text += "prompt_template:\n---\n"
    log_text += prompt_template
    log_text += "---\n"
    log_text += f"temperature: {str(temperature)}\n"
    log_text += "----init\n"
    log_text += f"initial aux data: {str(initial_aux_data)}\n"

    response = app_to_test.process(request, initial=True)
    print("response: " + str(response))
    print("SYS> " + response['system_utterance'])
    result['dialogue'].append({"speaker": "system", "utterance": response['system_utterance']})
    log_text += f"System: {response['system_utterance']}\n"
    yield log_text
    session_id = response['session_id']
    user_utterance = user_simulator.generate_next_user_utterance(prompt_template, response['system_utterance'])

    while True:
        result['dialogue'].append({"speaker": "user", "utterance": user_utterance})
        log_text += f"User: {user_utterance}\n"
        yield f"User: {user_utterance}\n"
        num_turns += 1
        print("USR> " + user_utterance)
        request = {"user_id": USER_ID, "session_id": session_id,
                   "user_utterance": user_utterance}
        print("request: " + str(request))
        response = app_to_test.process(request, initial=False)
        print("response: " + str(response))
        print("SYS> " + response['system_utterance'])
        result['dialogue'].append({"speaker": "system", "utterance": response['system_utterance']})
        log_text += f"System: {response['system_utterance']}\n"
        yield f"System: {response['system_utterance']}\n"
        if response['final'] or num_turns >= max_turns:
            break

        # next utterance
        user_utterance = user_simulator.generate_next_user_utterance(prompt_template, response['system_utterance'])

    print(log_text)

    if out_fp:
        print(log_text, file=out_fp)

    return result


