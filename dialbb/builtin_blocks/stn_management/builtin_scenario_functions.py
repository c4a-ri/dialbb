#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# builtin_scenario_functions.py
#   defines functions to be used in scenarios
#   組み込みシナリオ関数

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Any


def builtin_set(variable: str, value: str, context: Dict[str, Any]) -> None:
    """
    sets a value to a variable in the dialogue context
    対話文脈の変数に値をセットする
    :param variable: name of variable to set 値をセットする対話文脈の変数の名前
    :param value: value to set セットする値
    :param context: dialogue context 対話文脈
    :return: None
    """
    context[variable] = value


def builtin_eq(x: str, y: str, context: Dict[str, Any]) -> bool:
    """
    checks if two values are equal
    値が同じかどうか調べる
    :param x: 値1
    :param y: 値2
    :param context: 対話文脈（不使用）
    :return: True when x and y are the same
    """
    return x == y


def builtin_ne(x: str, y: str, context: Dict[str, Any]) -> bool:
    """
    checks if two values are equal
    値が違うかどうか調べる
    :param x: 値1
    :param y: 値2
    :param context: 対話文脈（不使用）
    :return: True when x and y are different
    """
    return x != y


def builtin_contains(x: str, y: str, context: Dict[str, Any]) -> bool:
    """
    checks if string x contains string y
    文字列xが文字列yを含むかどうか調べる
    :param x: 値1
    :param y: 値2
    :param context: 対話文脈（不使用）
    :return: True when x contains y
    """
    return y in x


def builtin_not_contains(x: str, y: str, context: Dict[str, Any]) -> bool:
    """
    returns True if string x does not contain string y
    文字列xが文字列yを含まないときにTrueを返す
    :param x: 値1
    :param y: 値2
    :param context: 対話文脈（不使用）
    :return: True when x doesn't contain y
    """
    return y not in x


def builtin_member_of(x: str, y: str, context: Dict[str, Any]) -> bool:
    """
    checks if string x is a member of y (list of string concatenated with colons)
    文字列xが文字列のリストyのメンバかどうか調べる。(yは文字列をコロンで連結したもの）
    :param x: 値1
    :param y: 値2 e.g. "apple:orange:pineapple"
    :param context: 対話文脈（不使用）
    :return: True when x is a member of y
    """
    return x in [m.strip() for m in y.split(":")]


def builtin_not_member_of(x: str, y: str, context: Dict[str, Any]) -> bool:
    """
    checks if string x is not a member of y (list of string concatenated with colons)
    文字列xが文字列のリストyのメンバでないときTrueを返す。(yは文字列をコロンで連結したもの）
    :param x: 値1
    :param y: 値2 e.g. "apple:orange:pineapple"
    :param context: 対話文脈（不使用）
    :return: True when x is a not member of y
    """
    return x not in [m.strip() for m in y.split(":")]


def builtin_is_long_silence(context: Dict[str, Any]) -> bool:
    """
    checks if input is detection of a long silence
    入力が長い沈黙の検出結果の場合 Trueを返す
    :return: True when input is a long silence, False otherwise
    """
    return context['aux_data'].get('long_silence', False)


def builtin_confidence_is_low(context: Dict[str, Any]) -> bool:
    """
    check if the confidence is low
    :return: True if the confidence of the input is lower than threshould
    """

    if context['_block_config'].get('ask_repetition') \
        and context['_block_config']['ask_repetition'].get("confidence_threshold"):
        if context['aux_data'].get("confidence"):
            if context['aux_data']["confidence"] < context['_block_config']['ask_repetition']["confidence_threshold"]:
                return True
            else:
                return False
        else:
            print("warning: confidence is not in the aux_data.")
            return False
    else:
        print("warning: confidence_threshold is not specified in the configuration.")
        return False

