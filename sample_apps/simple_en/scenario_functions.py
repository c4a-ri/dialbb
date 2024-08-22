#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# scenario_functions.py
#   functions used in sandwich app

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import Dict, Any


def is_known_sandwich(sandwich: str, context: Dict[str, Any]) -> bool:

    return sandwich in ("chicken salad sandwich", "egg salad sandwich", "roast beef sandwich")


def is_novel_sandwich(sandwich: str, context: Dict[str, Any]) -> bool:

    return not is_known_sandwich(sandwich, context)


