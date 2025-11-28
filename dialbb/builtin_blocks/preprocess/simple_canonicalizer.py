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
# simple_canonicalizer.py
#   canonicalize simply input string
#

import re
from dialbb.builtin_blocks.preprocess.abstract_canonicalizer import AbstractCanonicalizer


class SimpleCanonicalizer(AbstractCanonicalizer):

    def __init__(self, *args):
        super().__init__(*args)
        self._whitespace_pattern = re.compile(r"\s+")

    def canonicalize(self, input_text: str) -> str:
        """
        Implementation of Simple canonicalization
        :param input_text: input Japanese text
        :return: canonicalized text
        """
        result = input_text.strip()
        result = result.lower()
        result = result.replace("\n", " ")
        result = self._whitespace_pattern.sub(" ", result)
        return result
