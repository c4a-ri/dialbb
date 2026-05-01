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
# scenario_functions.py
#   functions used in sandwich app

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


import sys
import traceback
from datetime import datetime
from typing import Dict, Any
import os


def is_known_sandwich(sandwich: str, context: Dict[str, Any]) -> bool:

    return sandwich in ("chicken salad sandwich", "egg salad sandwich", "roast beef sandwich")


def is_novel_sandwich(sandwich: str, context: Dict[str, Any]) -> bool:

    return not is_known_sandwich(sandwich, context)


def decide_greeting(greeting_variable: str, context: Dict[str, Any]) -> None:
    """
    decide greeting utterance depending on the time
    :param greeting_variable: 挨拶を表す変数の名前
    :param context: 対話文脈
    """

    hour: int = datetime.now().hour
    if hour < 4:
        context[greeting_variable] = "Hello!"
    elif hour < 10:
        context[greeting_variable] = "Good Morning!"
    elif hour <= 19:
        context[greeting_variable] = "Hello!"
    else:
        context[greeting_variable] = "Good Evening!"


def generate_confirmation_request(nlu_result: Dict[str, Any], context: Dict[str, Any]) -> str:

    if nlu_result.get("type") == "tell-like-specific-sandwich" and nlu_result["slots"].get("favorite-sandwich"):
        return f'Do you like {nlu_result["slots"]["favorite-sandwich"]}?'
    else:
        return "Could you say that again?"


def get_system_name(context: Dict[str, Any]) -> str:

    return context['_config'].get("system_name", "Chatbot")

