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

# node types
NODE_TYPE_SYSTEM = "system"
NODE_TYPE_USER = "user"

# ノードID表示用
SHORT_ID_DIGITS = 6

DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
