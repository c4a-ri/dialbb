#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# scenario_functions.py
#   functions used in sandwich app

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'


import sys
import traceback
from datetime import datetime
from typing import Dict, Any
import os

use_openai: bool = False

openai_client = None

openai_api_key: str = os.environ.get('OPENAI_API_KEY', os.environ.get('OPENAI_KEY', ""))
if openai_api_key:
    import openai
    use_openai = True
    openai.api_key = openai_api_key
    openai_client = openai.OpenAI(api_key=openai_api_key)


def is_known_sandwich(sandwich: str, context: Dict[str, Any]) -> bool:

    return sandwich in ("chicken salad sandwich", "egg salad sandwich", "roast beef sandwich")


def is_novel_sandwich(sandwich: str, context: Dict[str, Any]) -> bool:

    return not is_known_sandwich(sandwich, context)


def decide_greeting(greeting_variable: str, context: Dict[str, Any]) -> None:
    """
    decide greeting utterance depending on the time
    :param greeting_variable: 挨拶を表す変数の名前
    :param context: 対話文脈
    """

    hour: int = datetime.now().hour
    if hour < 4:
        context[greeting_variable] = "Hello!"
    elif hour < 10:
        context[greeting_variable] = "Good Morning!"
    elif hour <= 19:
        context[greeting_variable] = "Hello!"
    else:
        context[greeting_variable] = "Good Evening!"


def generate_with_openai_gpt(prompt: str):

    chat_completion = None
    while True:
        try:
            chat_completion = openai_client.with_options(timeout=10).chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
        except openai.APITimeoutError:
            continue
        except Exception as e:
            print("OpenAI Error: " + traceback.format_exc())
            sys.exit(1)
        finally:
            if not chat_completion:
                continue
            else:
                break
    generated_utterance: str = chat_completion.choices[0].message.content
    return generated_utterance


def set_impression_of_dialogue(impression_key: str, context: Dict[str, Any]) -> None:

    if use_openai:

        prompt = "Generate the system's short utterance following the dialogue below to say the system's impression."
        for turn in context["_dialogue_history"]:
            if turn["speaker"] == 'user':
                prompt += f"User: {turn['utterance']}\n"
            else:
                prompt += f"System: {turn['utterance']}\n"

        generated_utterance: str = generate_with_openai_gpt(prompt)
        impression = generated_utterance.replace("System:", "")

    else:
        impression = "I see."

    context[impression_key] = impression


def generate_confirmation_request(nlu_result: Dict[str, Any], context: Dict[str, Any]) -> str:

    if nlu_result.get("type") == "tell-like-specific-sandwich" and nlu_result["slots"].get("favorite-sandwich"):
        return f'Do you like {nlu_result["slots"]["favorite-sandwich"]}?'
    else:
        return "Could you say that again?"



