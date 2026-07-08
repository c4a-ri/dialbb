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

# constants.py
#   defines shared constants
#

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

# main.py
#   dialbb no_code GUI main program
#

"""共有定数（`pyeditor` 内で利用）

ここにはノード種別のデフォルトリストや初期種別を置きます。
"""

import os

INITIAL_NODE_KIND = "initial"

DEFAULT_NODE_KINDS = [
    INITIAL_NODE_KIND,
    "error",
    "final",
    "other",
    "prep",
]

# ノードサイズ（固定レイアウト方針）
NODE_W = 140
NODE_H = 200
NODE_H_SYSTEM = 160
NODE_H_USER = 260

# QTextEdit高さ（ノード内の表示用）
SYS_UTTERANCE_H = 35
USR_CONDITION_H = 40
USR_ACTION_H = 30

# ノードの角丸・ヘッダ
NODE_CORNER_R = 12
NODE_HEADER_H = 34

# コネクタ
CONNECTOR_R = 6

# boundingRect余白
SHADOW_DX = 2
SHADOW_DY = 3
PAD = 8
CONNECTOR_OUTSIDE = -6

# Viewの初期表示倍率（1.0=100%）
INITIAL_VIEW_SCALE = 0.65

# JSON読み込み時の自動整列で使う開始X（左寄せ）
IMPORT_LAYOUT_BASE_X = -320.0

# node types
NODE_TYPE_SYSTEM = "system"
NODE_TYPE_USER = "user"

# ノードID表示用
SHORT_ID_DIGITS = 6

DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
