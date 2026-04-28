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
# prompt_template_en.py
#   defines prompt template for English dst_with_llm


PROMPT_TEMPLATE_EN: str = '''
# Task

Extract only the required slot values from the dialogue history and return a JSON object.
The format must be {"<slot name>": "<slot value>", ...}.
Do not include slots whose values are unknown.
Return JSON only.

# Slot types

{slot_definitions}

# Examples

{examples}

# Dialogue history

{dialogue_history}

'''