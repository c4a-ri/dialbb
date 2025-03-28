#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 C4A Research Institute, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# builtin_scenario_functions.py
#   defines functions to be used in scenarios
#   組み込みシナリオ関数

__version__ = '0.1'
__author__ = 'Mikio Nakano' 
__copyright__ = 'C4A Research Institute, Inc.'

import sys
import traceback
from typing import Dict, Any, List
import os

use_openai: bool = False

openai_client = None

openai_api_key: str = os.environ.get('OPENAI_API_KEY', os.environ.get('OPENAI_KEY', ""))
if openai_api_key:
    import openai
    use_openai = True
    openai.api_key = openai_api_key
    openai_client = openai.OpenAI(api_key=openai_api_key)

debug: bool = (os.environ.get('DIALBB_DEBUG', 'no').lower() == "yes")

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
    return context['_aux_data'].get('long_silence', False)


def builtin_confidence_is_low(context: Dict[str, Any]) -> bool:
    """
    check if the confidence is low
    :return: True if the confidence of the input is lower than threshold
    """

    if context['_block_config'].get("input_confidence_threshold"):
        if context['_aux_data'].get("confidence"):
            if context['_aux_data']["confidence"] < context['_block_config']["input_confidence_threshold"]:
                return True
            else:
                return False
        else:
            print("warning: confidence is not in the aux_data.")
            return False
    else:
        print("warning: confidence_threshold is not specified in the configuration.")
        return False


def builtin_num_turns_exceeds(threshold_str: str, context: Dict[str, Any]) -> bool:
    """
    Checks number of turns from the beginning of the session exceeds the threshold
    :param threshold_str:
    :param context:
    :return: True if exceeds
    """

    try:
        threshold: int = int(threshold_str)
    except ValueError:
        print("Warning: threshold for turns is not an integer: " + threshold_str)
        return False

    num_turns = 0
    for turn in context.get("_dialogue_history", []):
        if turn.get('speaker') == 'user':
            num_turns += 1
            if num_turns > threshold:
                return True
    else:
        return False


def builtin_num_turns_in_state_exceeds(threshold_str: str, context: Dict[str, Any]) -> bool:
    """
    Checks number of turns in the state exceeds the threshold
    :param threshold_str:
    :param context:
    :return: True if exceeds
    """

    try:
        threshold: int = int(threshold_str)
    except ValueError:
        print("Warning: threshold for turns is not an integer: " + threshold_str)
        return False

    return True if context.get("_turns_in_state", 0) > threshold else False

def create_prompt_for_chatgpt(task: str, language: str, system_persona: str, situation: str,
                              dialogue_history: List[Dict[str, str]]) -> str:

    """
    create prompt for chatgpt-based generation/condition check
    """

    prompt: str = ""

    if language == 'ja':
        word_situation: str = "状況"
        word_your_persona: str = "あなたのペルソナ"
        word_task: str = "タスク"
        word_dialogue_history: str = "今までの対話"
        word_user: str = "ユーザ"
        word_system: str = "システム"
    else:
        word_situation: str = "Situation"
        word_your_persona: str = "Your persona"
        word_task: str = "Task"
        word_dialogue_history: str = "Dialogue up to now"
        word_user: str = "User"
        word_system: str = "System"

    if situation:
        prompt += f"# {word_situation}\n\n"
        for situation_element in situation:
            prompt += f"- {situation_element}\n"
        prompt += '\n'

    if system_persona:
        prompt += f"# {word_your_persona}\n\n"
        for persona_element in system_persona:
            prompt += f"- {persona_element}\n"
        prompt += '\n'

    dialogue_history_string: str = ""
    for turn in dialogue_history:
        if turn["speaker"] == 'user':
            dialogue_history_string += f"{word_user}: {turn['utterance']}\n"
        elif turn["speaker"] == 'system':
            dialogue_history_string += f"{word_system}: {turn['utterance']}\n"
        else:  # multi party. use user_id.
            dialogue_history_string += f"{turn['speaker']}: {turn['utterance']}\n"

    prompt += f"# {word_dialogue_history}\n\n" + dialogue_history_string

    prompt += f"# {word_task}\n\n" + task + "\n\n"

    return prompt


def builtin_generate_with_llm(task: str, context: Dict[str, Any]) -> str:
    """
    Judge if the condition is satisfied using ChatGPT
    :param task: instruction
    :param context: dialogue context
    :return: true if satisfied and false otherwise
    """

    if use_openai:

        language: str = context['_config'].get("language")
        if language == 'ja':
            system_name: str = "システム"
        else:
            system_name: str = "System"

        # read chatgpt settings in the block config
        chatgpt_settings: Dict[str, Any] = context['_block_config'].get("chatgpt")
        if chatgpt_settings:
            gpt_model: str = chatgpt_settings.get("gpt_model", "gpt-4o-mini")
            gpt_temperature: float = chatgpt_settings.get("temperature", 0.7)
            system_persona: List[str] = chatgpt_settings.get("persona")
            situation: List[str] = chatgpt_settings.get("situation")
        else:
            gpt_model: str = "gpt-4o-mini"
            gpt_temperature: float = 0.7
            system_persona: str = ""
            situation: str = ""

        dialogue_history: List[Dict[str, str]] = context['_dialogue_history']

        if language == 'ja':
            task = task + "あなたの名前は含めないでください。"
        else:
            task = task + "Please don't include your name."

        prompt: str = create_prompt_for_chatgpt(task, language, system_persona, situation, dialogue_history)
        if debug:
            print("prompt: \n" + prompt)

        chat_completion = None
        while True:
            try:
                chat_completion = openai_client.with_options(timeout=10).chat.completions.create(
                    model=gpt_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=gpt_temperature,
                )
            except openai.APITimeoutError:
                continue
            except Exception as e:
                print("OpenAI Error: " + traceback.format_exc())
            finally:
                if not chat_completion:
                    continue
                else:
                    break

        generated_utterance: str = chat_completion.choices[0].message.content
        if debug:
            print("utterance generated by chatgpt: " + generated_utterance, flush=True)
        generated_utterance = generated_utterance.replace(f'{system_name}:', '').strip()  # remove 'System: '
        return generated_utterance
    else:
        return "..."


def builtin_check_with_llm(task: str, context: Dict[str, Any]) -> bool:
    """
    Check if the condition is satisfied
    :param task: instruction
    :param context: dialogue context
    :return: true if the condition is satisfied
    """

    if use_openai:

        language: str = context['_config'].get("language")

        # read chatgpt settings in the block config
        chatgpt_settings: Dict[str, Any] = context['_block_config'].get("chatgpt")
        if chatgpt_settings:
            gpt_model: str = chatgpt_settings.get("gpt_model", "gpt-4o-mini")
            gpt_temperature: float = chatgpt_settings.get("temperature_for_checking", 0.7)
            system_persona: List[str] = chatgpt_settings.get("persona")
            situation: List[str] = chatgpt_settings.get("situation")
        else:
            gpt_model: str = "gpt-4o-mini"
            gpt_temperature: float = 0.7
            system_persona: str = ""
            situation: str = ""

        dialogue_history: List[Dict[str, str]] = context['_dialogue_history']

        if language == 'ja':
            task = task + "YesかNoのどちらかで答えてください。"
        else:
            task = task + "Please answer with yes or no."

        prompt: str = create_prompt_for_chatgpt(task, language, system_persona, situation, dialogue_history)

        if debug:
            print("prompt: \n" + prompt)

        chat_completion = None
        while True:
            try:
                chat_completion = openai_client.with_options(timeout=10).chat.completions.create(
                    model=gpt_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=gpt_temperature,
                )
            except openai.APITimeoutError:
                continue
            except Exception as e:
                print("OpenAI Error: " + traceback.format_exc())
            finally:
                if not chat_completion:
                    continue
                else:
                    break
        response: str = chat_completion.choices[0].message.content
        if debug:
            print("response from chatgpt: " + response, flush=True)
        response = response.lower()
        if response.find("yes") == -1:  # yes was not found
            return False
        else:
            return True
    else:
        print ("Error: can't use openai")
        return False


