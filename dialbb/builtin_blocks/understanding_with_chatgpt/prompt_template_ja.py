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
# prompt_template_ja.py
#   defines prompt templates for chatgpt understander


PROMPT_TEMPLATE_JA: str = '''
# タスク

入力発話を発話タイプに分類するとともに、スロットを抽出してJSON形式で返してください。

# 発話タイプの種類

@types

# スロットの種類

@slot_definitions

# 例

@examples

# 入力

@input

'''

