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
from collections.abc import Generator

import yaml
import os, sys

from dialbb.main import DialogueProcessor
from dialbb.sim_tester.test_with_dialbb_app import test_with_dialbb
from dialbb.sim_tester.test_with_llm import test_with_llm

def do_test(test_config_file: str,
            app_config_file: str,
            output_file: str | None = None,
            json_output: bool = False,
            prompt_params: dict[str, str] | None = None) -> Generator[str, None, None]:
    """
    test using LLM-based simulator
    :param test_config_file: config file for test
    :param app_config_file: config file for dialbb app to test
    :param output_file: file to output log
    :param json_output: if True, output file will be JSON
    :param prompt_params: parameters to replace tags in prompt
    :return: list of logs in JSON format
    """

    app_to_test: DialogueProcessor = DialogueProcessor(app_config_file)

    test_config_dir: str = os.path.dirname(test_config_file)
    with open(test_config_file, encoding='utf-8') as fp:
        test_config: dict[str, object] = yaml.safe_load(fp)

    if test_config.get("configs"):
        yield from test_with_dialbb(test_config, test_config_dir, app_to_test, output_file, json_output)
    elif test_config.get("settings"):
        yield from test_with_llm(test_config, test_config_dir, app_to_test, output_file, json_output, prompt_params)
    else:
        raise Exception("Either configs or settings must be specified in the test configuration.")




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
        for result in do_test(
                test_config_file,
                app_config_file,
                output_file=args.output,
                json_output=args.json_output):
            pass
    else:
        for result in do_test(test_config_file, app_config_file):
            # print(f"##>{result}", end="")
            pass



if __name__ == '__main__':
    main()
