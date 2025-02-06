#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# prompt_template_en.py
#   defines prompt templates for chatgpt understander


PROMPT_TEMPLATE_EN: str = '''
# Task

Extract named entities in the input utterance, and return them in JSON format.

# named entity classes

@classes

# Explanations on the named entity classes

@class_explanations

# Examples of named entities

@ne_examples

# Examples of named entity recognition results

@ner_examples

# Input utterance

@input

'''


