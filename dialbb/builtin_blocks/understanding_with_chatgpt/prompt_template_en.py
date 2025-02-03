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
#   defines prompt templates for chatgpt understander


PROMPT_TEMPLATE_EN: str = '''
# Task

Classify the input into one of the utterance types, extract slots, and return them in JSON format.

# Utterance types

@types

# Kinds of slots

@slot_definitions

# Examples

@examples

# Input

@input

'''


