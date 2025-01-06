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
#   functions used in sample Japanese app
#   日本語サンプルアプリで用いるシナリオ関数

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import sys
import traceback
from datetime import datetime
from typing import Dict, Any
import os

use_openai: bool = False

openai_client = None

openai_api_key: str = os.environ.get('OPENAI_API_KEY', os.environ.get('OPENAI_KEY', ""))
if openai_api_key:
    import openai
    use_openai = True
    openai.api_key = openai_api_key
    openai_client = openai.OpenAI(api_key=openai_api_key)


# 知っているラーメンの種類
known_ramens = ("豚骨ラーメン", "味噌ラーメン", "塩ラーメン", "醤油ラーメン")


def is_known_ramen(ramen: str, context: Dict[str, Any]) -> bool:
    """
    知っているラーメンかどうか
    :param ramen: ラーメンの種類名
    :param context: 対話文脈（未使用）
    :return: 知っていたらTrue, さもなくばFalse
    """
    return ramen in known_ramens


def is_novel_ramen(ramen: str, context: Dict[str, Any]) -> bool:
    """
    知らないラーメンかどうか
    :param ramen: ラーメンの種類名
    :param context: 対話文脈（未使用）
    :return: 知らないならTrue, 知っていればFalse
    """
    return ramen not in known_ramens


# ラーメンの種類と地域の関係
ramen_map = {"豚骨ラーメン": "博多",
             "味噌ラーメン": "札幌",
             "塩ラーメン": "函館",
             "醤油ラーメン": "東京"}


def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None:
    """
    ラーメンの種類からその発祥の地域を得て、対話文脈に保持する
    :param ramen: ラーメンの種類
    :param variable: 地域名を蓄える変数の名前
    :param context: 対話文脈
    """
    location:str = ramen_map.get(ramen, "日本")
    context[variable] = location


def decide_greeting(greeting_variable: str, context: Dict[str, Any]) -> None:
    """
    挨拶文を時間帯に応じて決める
    :param greeting_variable: 挨拶を表す変数の名前
    :param context: 対話文脈
    """

    hour: int = datetime.now().hour
    if hour < 4:
        context[greeting_variable] = "こんばんは"
    elif hour < 10:
        context[greeting_variable] = "おはようございます"
    elif hour <= 19:
        context[greeting_variable] = "こんにちは"
    else:
        context[greeting_variable] = "こんばんは"


def generate_confirmation_request(nlu_result: Dict[str, Any], context: Dict[str, Any]) -> str:

    if nlu_result.get("type") == "特定のラーメンが好き" and nlu_result["slots"].get("好きなラーメン"):
        return f'{nlu_result["slots"]["好きなラーメン"]}がお好きなんですか？'
    else:
        return "もう一度言って頂けますか？"


def get_system_name(context: Dict[str, Any]) -> str:

    return context['_config'].get("system_name", "チャットボット")







