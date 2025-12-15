#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 C4A Research Institute, Inc.
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
# main.py
#   automatically testing app
#   自動テスト用スクリプト

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


import argparse
import json
import traceback
from typing import Dict, Any, Generator, List
import yaml
import os, sys

from dialbb.main import DialogueProcessor
from dialbb.sim_tester.llm_tester import LLMTester

DEFAULT_MAX_TURNS: int = 15
DEFAULT_TEMPERATURE: float = 0.7
USER_ID: str = "user1"


def test_one_setting(
    user_simulator,
    dialogue_processor,
    setting: Dict[str, Any],
    temperature: float,
    max_turns: int,
    out_fp,
) -> Generator[str, None, Dict[str, Any]]:
    result = {}

    initial_aux_data: Dict[str, Any] = setting['initial_aux_data']
    prompt_template: str = setting['prompt_template']
    user_simulator.set_parameters_and_clear_history(prompt_template, temperature)

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

    response = dialogue_processor.process(request, initial=True)
    print("response: " + str(response))
    print("SYS> " + response['system_utterance'])
    result['dialogue'].append({"speaker": "system", "utterance": response['system_utterance']})
    log_text += f"System: {response['system_utterance']}\n"
    yield log_text
    session_id = response['session_id']
    user_utterance = user_simulator.generate_next_user_utterance(response['system_utterance'])

    while True:
        result['dialogue'].append({"speaker": "user", "utterance": user_utterance})
        log_text += f"User: {user_utterance}\n"
        yield f"User: {user_utterance}\n"
        num_turns += 1
        print("USR> " + user_utterance)
        request = {"user_id": USER_ID, "session_id": session_id,
                   "user_utterance": user_utterance}
        print("request: " + str(request))
        response = dialogue_processor.process(request, initial=False)
        print("response: " + str(response))
        print("SYS> " + response['system_utterance'])
        result['dialogue'].append({"speaker": "system", "utterance": response['system_utterance']})
        log_text += f"System: {response['system_utterance']}\n"
        yield f"System: {response['system_utterance']}\n"
        if response['final'] or num_turns >= max_turns:
            break

        # next utterance
        user_utterance = user_simulator.generate_next_user_utterance(response['system_utterance'])

    print(log_text)

    if out_fp:
        print(log_text, file=out_fp)

    return result


def test_by_simulation(test_config_file: str, app_config_file: str, output_file: str = None,
                       json_output: bool = False,
                       prompt_params: Dict[str, str] = None) -> Generator[str, None, None]:
    """
    test using LLM-based simulator
    :param test_config_file: config file for test
    :param app_config_file: config file for dialbb app to test
    :param output_file: file to output log
    :param json_output: if True, output file will be JSON
    :param prompt_params: parameters to replace tags in prompt
    :return: list of logs in JSON format
    """

    dialogue_processor = DialogueProcessor(app_config_file)

    test_config_dir: str = os.path.dirname(test_config_file)
    with open(test_config_file, encoding='utf-8') as fp:
        test_config: Dict[str, Any] = yaml.safe_load(fp)

    # read settings
    settings: List[Dict[str, Any]] = []
    setting_descriptions: List[Dict[str, str]] = test_config.get("settings")
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
        initial_aux_data_file: str = setting_description.get("initial_aux_data")
        if initial_aux_data_file:
            file: str = os.path.join(test_config_dir, initial_aux_data_file)
            try:
                with open(file, encoding='utf-8') as fp:
                    initial_aux_data: Dict[str, any] = json.load(fp)
            except Exception as e:
                print(traceback.format_exc())
                print("problem with reading json file: " + file)
                sys.exit(1)

        settings.append({"prompt_template": prompt_template, "initial_aux_data": initial_aux_data})

    # temperature list
    temperatures: List[float] = test_config.get("temperatures", [DEFAULT_TEMPERATURE])

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
                dialogue_processor,
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


def main():
    # read arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--app_config", help="dialbb app config yaml file", required=True)
    parser.add_argument("--test_config", help="test_config", required=True)  # config
    parser.add_argument("--output", help="output file", required=False)  # output file (same format with test file)
    parser.add_argument("--json_output", help="output file", action='store_true')  # output file (same format with test file)
    args = parser.parse_args()

    app_config_file: str = args.app_config
    test_config_file: str = args.test_config
    if args.output:
        test_by_simulation(test_config_file, app_config_file, output_file=args.output, json_output=args.json_output)
    else:
        for result in test_by_simulation(test_config_file, app_config_file):
            # print(f"##>{result}", end="")
            pass


if __name__ == '__main__':
    main()
