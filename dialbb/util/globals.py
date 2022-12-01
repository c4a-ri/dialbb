#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# globals.py
#   define global variables
#   グローバル変数を定義

import os

DEBUG: bool = False  # debug mode or not
if os.environ.get("DIALBB_DEBUG", "no").lower() in ('yes', 'true'):
    DEBUG = True

