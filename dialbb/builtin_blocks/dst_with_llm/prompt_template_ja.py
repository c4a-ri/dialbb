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
#   defines prompt template for Japanese dst_with_llm


PROMPT_TEMPLATE_JA: str = '''
# タスク

ここまでの対話から必要なスロット値だけを抽出して、JSONオブジェクトで返してください。
返す形式は {"<slot name>": "<slot value>", ...} です。
値が分からないスロットは含めないでください。
JSON以外は返さないでください。

# スロットの種類

{slot_definitions}

# 例

{examples}

# ここまでの対話

{dialogue_history}

'''
