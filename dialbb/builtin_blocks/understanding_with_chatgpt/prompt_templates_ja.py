#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# prompt_templates_ja.py
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

