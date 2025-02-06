#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# prompt_template_ja.py
#   defines prompt template for chatgpt NER


PROMPT_TEMPLATE_JA: str = '''
# タスク

入力発話の中の固有表現を抽出し、JSON形式で返してください。

# 固有表現のクラス

@lasses

# 固有表現のクラスの説明

@class_explanations

# 固有表現の例

@ne_examples

# 固有表現抽出結果の例

@ner_examples

# 入力発話

@input

'''

