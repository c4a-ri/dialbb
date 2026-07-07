#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright C4A Research Institute, Inc.
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
# constants.py
#   define constants


import os


# GUI表示テキストのデフォルト設定（定数データ）
# - GUI_TEXT_DEFAULT_FILE: 多言語テキストYAMLの既定パス
# - GUI_TEXT_DEFAULT_LANG: 初期言語
GUI_TEXT_DEFAULT_FILE: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "gui_nc_text.yml")
)
GUI_TEXT_DEFAULT_LANG: str = "ja"
