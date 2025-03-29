#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
from typing import Dict, Any, List, Union
import yaml
import os, sys

from dialbb.main import DialogueProcessor
from chatgpt_tester import ChatGPTTester

DEFAULT_MAX_TURNS = 15
USER_ID = "user1"
TASk_DESCRIPTION_TAG = '@task_description'

if __name__ == '__main__':

    # read arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--app_config", help="dialbb app config yaml file", required=True)
    parser.add_argument("--test_config", help="test_config", required=False)  # config
    parser.add_argument("--output", help="output file", required=False)  # output file (same format with test file)
    args = parser.parse_args()

    app_config_file: str = args.app_config
    dialogue_processor = DialogueProcessor(app_config_file)

    test_config_file: str = args.test_config
    test_config_dir: str = os.path.dirname(test_config_file)
    with open(test_config_file, encoding='utf-8') as fp:
        test_config: Dict[str, Any] = yaml.safe_load(fp)

    # read settings
    settings: List[Dict[str, Any]] = []
    setting_descriptions: List[Dict[str, str]] = test_config.get("settings")
    for setting_description in setting_descriptions:
        task_description: str = ""
        task_description_file: str = setting_description.get("task_description")
        if task_description_file:
            with open(os.path.join(test_config_dir, task_description_file), encoding='utf-8') as fp:
                task_description = fp.read()

        prompt_template_file = setting_description.get("prompt_template")
        if not prompt_template_file:
            print("no prompt template file specified.")
            sys.exit(1)
        with open(os.path.join(test_config_dir, prompt_template_file), encoding='utf-8') as fp:
            prompt_template = fp.read()
            if task_description:
                prompt_template = prompt_template.replace(TASk_DESCRIPTION_TAG, task_description)

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
    temperatures: List[float] = test_config.get("temperatures", [0.7])

    user_simulator = ChatGPTTester(test_config)

    log_text: str = ""

    max_turns = test_config.get('max_turns', DEFAULT_MAX_TURNS)

    # setting output file
    if args.output:
        out_fp = open(args.output, mode='w', encoding='utf-8')
    else:
        out_fp = None

    for setting in settings:
        for temperature in temperatures:

            initial_aux_data: Dict[str, Any] = setting['initial_aux_data']
            prompt_template: str = setting['prompt_template']
            user_simulator.set_parameters_and_clear_history(prompt_template, temperature)

            num_turns: int = 0

            # first turn

            log_text += "----settings\n"
            log_text += f"model: {user_simulator.get_gpt_model()}\n"
            log_text += "prompt_template:\n---\n"
            log_text += prompt_template
            log_text += "---\n"
            log_text += f"temperature: {str(temperature)}\n"
            log_text += "----init\n"
            request = {"user_id": USER_ID, "aux_data": initial_aux_data}  # initial request
            log_text += f"initial aux data: {str(initial_aux_data)}\n"
            result = dialogue_processor.process(request, initial=True)
            print("response: " + str(result))
            print("SYS> " + result['system_utterance'])
            log_text += f"System: {result['system_utterance']}\n"
            session_id = result['session_id']
            user_utterance = user_simulator.generate_next_user_utterance(result['system_utterance'])

            while True:
                num_turns += 1
                print("USR> " + user_utterance)
                log_text += f"User: {user_utterance}\n"
                request = {"user_id": USER_ID, "session_id": session_id,
                           "user_utterance": user_utterance}
                print("request: " + str(request))
                result = dialogue_processor.process(request, initial=False)
                print("response: " + str(result))
                print("SYS> " + result['system_utterance'])
                log_text += f"System: {result['system_utterance']}\n"
                if result['final'] or num_turns >= max_turns:
                    break

                # next utterance
                user_utterance = user_simulator.generate_next_user_utterance(result['system_utterance'])

            print(log_text)

            if out_fp:
                print(log_text, file=out_fp)

            log_text = ""

    if out_fp:
        out_fp.close()


