#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os


# GUI表示テキストのデフォルト設定（定数データ）
# - GUI_TEXT_DEFAULT_FILE: 多言語テキストYAMLの既定パス
# - GUI_TEXT_DEFAULT_LANG: 初期言語
GUI_TEXT_DEFAULT_FILE: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "gui_nc_text.yml")
)
GUI_TEXT_DEFAULT_LANG: str = "ja"
