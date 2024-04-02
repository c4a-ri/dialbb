#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

    try:
        threshold: int = int(threshold_str)
    except ValueError:
        print("Warning: threshold for turns is not an integer: " + threshold_str)
        return False

    num_turns = 0
    for turn in context.get("dialogue_history", []):
        if turn.get('speaker') == 'user':
            num_turns += 1
            if num_turns > threshold:
                return True
    else:
        return False


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

    prompt += f"# {word_task}\n\n" + task + "\n\n"

    dialogue_history_string: str = ""
    for turn in dialogue_history:
        if turn["speaker"] == 'user':
            dialogue_history_string += f"{word_user}: {turn['utterance']}\n"
        else:
            dialogue_history_string += f"{word_system}: {turn['utterance']}\n"

    prompt += f"# {word_dialogue_history}\n\n" + dialogue_history_string

    return prompt


def builtin_generate_with_chatgpt(task: str, context: Dict[str, Any]) -> bool:
    """
    Judge if the condition is satisfied using ChatGPT
    :param task: instruction
    :param context: dialogue context
    :return: true if satisfied and false otherwise
    """

    if use_openai:

        language: str = context['_config'].get("language")

        # read chatgpt settings in the block config
        chatgpt_settings: Dict[str, Any] = context['_block_config'].get("chatgpt")
        if chatgpt_settings:
            gpt_model: str = chatgpt_settings.get("model", "gpt-3.5-turbo")
            gpt_temperature: float = chatgpt_settings.get("temperature", 0.7)
            system_persona: List[str] = chatgpt_settings.get("persona")
            situation: List[str] = chatgpt_settings.get("situation")
        else:
            gpt_model: str = "gpt-3.5-turbo"
            gpt_temperature: float = 0.7
            system_persona: str = ""
            situation: str = ""

        dialogue_history: List[Dict[str, str]] = context['_dialogue_history']

        if language == 'ja':
            task = task + "YesかNoで答えてください。"
        else:
            task = task + "Please answer with yes or no."

        prompt: str = create_prompt_for_chatgpt(task, language, system_persona, situation, dialogue_history)

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
        response = response.lower()
        if response.find("yes") == -1:
            return False
        else:
            return True
    else:
        print ("Error: can't use openai")
        return False


def builtin_check_with_chatgpt(task: str, context: Dict[str, Any]) -> bool:
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
            gpt_model: str = chatgpt_settings.get("model", "gpt-3.5-turbo")
            gpt_temperature: float = chatgpt_settings.get("temperature", 0.7)
            system_persona: List[str] = chatgpt_settings.get("persona")
            situation: List[str] = chatgpt_settings.get("situation")
        else:
            gpt_model: str = "gpt-3.5-turbo"
            gpt_temperature: float = 0.7
            system_persona: str = ""
            situation: str = ""

        dialogue_history: List[Dict[str, str]] = context['_dialogue_history']

        task_json_mode = task + ""

        prompt: str = create_prompt_for_chatgpt(task, language, system_persona, situation, dialogue_history)

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
        generated_utterance = generated_utterance.replace(f'{system_name}:', '').strip()  # remove 'System: '
        return generated_utterance
    else:
        return "..."




def builtin_num_turns_exceeds(threshold_string: str, context: Dict[str, Any]) -> bool:
    """
    check if the number of turns so far exceeds the threshold
    :param threshold_string: threshold (string)
    :param context: dialogue context
    :return: true if it exceeds
    """

    threshold: int = int(threshold_string)

    num_turns = 0
    for turn in context['_dialogue_history']:
        if turn["speaker"] == 'user':
            num_turns += 1
    if num_turns >= threshold:
        return True
    else:
        return False

