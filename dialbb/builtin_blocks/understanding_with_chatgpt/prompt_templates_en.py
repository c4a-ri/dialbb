#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# prompt_templates_en.py
#   defines prompt templates for chatgpt understander


PROMPT_TEMPLATE_EN: str = '''
# Task

Classify the input into one of the utterance types, extract slots, and return them in JSON format.

# Utterance types

@types

# Kinds of slots

@slot_definitions

# Examples

@examples

# Input

@input

'''


