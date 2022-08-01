#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# globals.py
#   define global variables

import os

DEBUG: bool = False
if os.environ.get("DIALBB_DEBUG", "no").lower() in ('yes', 'true'):
    DEBUG = True

