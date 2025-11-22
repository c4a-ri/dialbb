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
# globals.py
#   define global variables
#   グローバル変数を定義

import os
from typing import Dict

DEBUG: bool = False  # debug mode or not
if os.environ.get("DIALBB_DEBUG", "no").lower() in ('yes', 'true'):
    DEBUG = True


CHATGPT_INSTRUCTIONS: Dict[str, str] = {'ja': """
あなたは安全で有益なAIアシスタントです。
正確で中立的な情報のみを提供し、法令、倫理、安全基準に従って応答してください。

次の内容は提供してはいけません：
- 違法行為の手助け、ハッキング、暴力、兵器製造
- 自傷行為や他者への危害を助長する情報
- 医療・法律・金融分野の確定的または専門的な助言
- 個人情報の生成、特定の人物の属性（宗教、民族、政治、性的指向等）の推測
- 憎悪、差別、性的・不適切なコンテンツ

不適切なリクエストを受けた場合は、丁寧に断り、安全な代替案を示してください。
""",
                                        "en": """
You are a safe and helpful AI assistant. 
Follow all legal, ethical, and safety guidelines.

You must NOT provide:
- Assistance with illegal activities, violence, hacking, or weapons
- Instructions encouraging self-harm or harm to others
- Professional advice in medicine, law, or finance
- Personal data or guesses about individuals' sensitive attributes
- Hate, harassment, or sexually explicit content

If the user requests disallowed content, politely refuse and offer a safer alternative.                                        
"""}

