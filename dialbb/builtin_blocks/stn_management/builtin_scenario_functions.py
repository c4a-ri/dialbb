#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# builtin_scenario_functions.py
#   defines functions to be used in scenarios

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Any


def builtin_set(variable: str, value: str, context: Dict[str, Any]):
    context[variable] = value


def builtin_eq(x: str, y: str, context: Dict[str, Any]) -> bool:
    return x == y


def builtin_ne(x: str, y: str, context: Dict[str, Any]) -> bool:
    return x != y


def builtin_contains(x: str, y: str, context: Dict[str, Any]) -> bool:
    return y in x


def builtin_not_contains(x: str, y: str, context: Dict[str, Any]) -> bool:
    return y not in x


def builtin_member_of(x: str, y: str, context: Dict[str, Any]) -> bool:
    return x in [m.strip() for m in y.split(":")]


def builtin_not_member_of(x: str, y: str, context: Dict[str, Any]) -> bool:
    return x not in [m.strip() for m in y.split(":")]
