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
# state_transition_network.py
#   classes for representing state transition networks
#   状態遷移ネットワークを表現するクラス群

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import re
from typing import List, Dict, Any
from dialbb.util.error_handlers import abort_during_building, warn_during_building
from dialbb.util.globals import DEBUG
CONSTANT: str = "constant"
SPECIAL_VARIABLE: str = "special_variable"
VARIABLE: str = "variable"
ADDRESS: str = "address"
PREP_STATE_NAME: str = "#prep"
INITIAL_STATE_NAME: str = "#initial"
FINAL_STATE_PREFIX: str = "#final"
ERROR_STATE_NAME: str = "#error"
FINAL_ABORT_STATE_NAME: str = "#final_abort"
BUILTIN_FUNCTION_PREFIX: str = "builtin"
GOSUB: str = "#gosub"
EXIT: str = "#exit"
SKIP: str = "$skip"
COMMA: str = "&&&comma&&&"
SEMICOLON: str = "&&&semicolon&&&"
LEFTPAREN: str = "&&&leftparen&&&"
RIGHTPAREN: str = "&&&rightparen&&&"
DOUBLEQUOTE: str = "&&&doublequote&&&"

function_call_pattern = re.compile(r"([^(]+)\(([^)]*)\)", re.DOTALL)  # matches function patter such as "func(..)"
ne_condition_pattern = re.compile("([^=]+)!=(.+)")  # matches <variable>!=<value>
eq_condition_pattern = re.compile("([^=]+)==(.+)")  # matches <variable>==<value>
set_action_pattern = re.compile("([^=]+)=(.+)")  # matches <variable>=<value>
num_turns_exceeds_pattern = re.compile(r'TT\s*>\s*(\d+)')  # matches TT><n> such as "TT>3"
num_turns_in_state_exceeds_pattern = re.compile(r'TS\s*>\s*(\d+)')   #  matches TS><n> e.g. "TS > 4"


class Argument:
    """
    Argument of scenario functions
    シナリオ関数の引数を表すクラス
    """

    def __init__(self, argument_string: str):

        if argument_string[0] in ('#', '＃'):  # special variable 特殊変数
            self._type = SPECIAL_VARIABLE
            self._name = argument_string[1:]
        elif argument_string[0] in ('*', '＊'):  # variable value e.g., *aaa 変数の値
            self._type = VARIABLE
            self._name = argument_string[1:]
        elif argument_string[0] in ('"', '”', '“') and argument_string[-1] in ('"', '”', '“'):  # constant string 定数文字列
            self._type = CONSTANT
            self._name = (argument_string[1:-1].replace(SEMICOLON, ';')
                          .replace(COMMA, ",")
                          .replace(LEFTPAREN, "(")
                          .replace(RIGHTPAREN, ")")
                          .replace(DOUBLEQUOTE, '"')) # revert semicolon, comma, etc
        elif argument_string[0] in ('&', '＆'):  # variable name 変数名
            self._type = ADDRESS
            self._name = argument_string[1:]  # remove '&'
        else:
            warn_during_building(f"'{argument_string}' is not a valid argument. " +
                                 "It's not a special variable, variable, constant, nor address.")

    def __str__(self):
        return f"Argument: type={self._type}, name={self._name}"

    def is_special_variable(self) -> bool:
        """
        returns True if this is a special variable
        特殊変数ならTrueを返す
        """
        return self._type == SPECIAL_VARIABLE

    def is_variable(self) -> bool:
        """
        returns True if this is a variable
        変数ならTrueを返す
        """
        return self._type == VARIABLE

    def is_constant(self) -> bool:
        """
        returns True if this is a constant
        定数文字列ならTrueを返す
        """
        return self._type == CONSTANT

    def is_address(self) -> bool:
        """
        returns True if this is a variable name
        変数名ならTrueを返す
        """
        return self._type == ADDRESS

    def get_name(self) -> str:
        """
        returns name of this argument
        名前を返す
        :return: name
        """
        return self._name


class Condition:
    """
    a condition for state transition
    状態遷移の条件を表すクラス
    """

    def __init__(self, function_name: str, arguments: List[Argument], string_representation: str):

        self._condition_function = function_name
        if function_name[0] == '_':  # builtin function 組み込み関数
            # add builtin function prefix
            self._condition_function = BUILTIN_FUNCTION_PREFIX + self._condition_function
        self._arguments: List[Argument] = arguments  # list of arguments 引数のリスト
        self._string_representation: str = string_representation  # representation used in loggging etc. log等での表記

    def __str__(self) -> str:
        return self._string_representation

    def get_function(self) -> str:
        """
        returns the name of the function of this condition
        この条件の関数の名前を返す
        :return: the function name
        """
        return self._condition_function

    def get_arguments(self) -> List[Argument]:
        """
        returns the list of arguments of this condition
        この条件の引数のリスト返す
        :return: the list of Argument objects
        """
        return self._arguments


class Action:
    """
    an action at a state transition
    状態遷移におけるアクション
    """

    def __init__(self, function_name: str, arguments: List[Argument], string_representation: str):
        self._command_name: str = function_name  # function name コマンド関数名
        if function_name[0] == '_':  # builtin function
            self._command_name = BUILTIN_FUNCTION_PREFIX + self._command_name
        self._arguments: List[Argument] = arguments  # list of arguments 引数のリスト
        self._string_representation = string_representation  # representation used in logging log等での表記

    def __str__(self):
        return self._string_representation

    def get_function_name(self) -> str:
        """
        returns the name of command
        コマンドの名前を返す
        :return: command name string
        """
        return self._command_name

    def get_arguments(self) -> List[Argument]:
        """
        returns the argument list
        引数のリストを返す
        :return: list of Argument objects
        """
        return self._arguments


class Transition:
    """
    Class for representing transition
    遷移を表すクラス
    """

    def __init__(self, user_utterance_type: str, conditions_str: str, actions_str: str, destination: str):
        if DEBUG:
            print(f"creating transition: user utterance type: {user_utterance_type}, " +
                  f"conditions: {conditions_str}, actions: {actions_str}, destinations: {destination}")
        self._user_utterance_type: str = user_utterance_type.strip()
        self._conditions: List[Condition] = []
        conditions_str = self.replace_special_characters_in_constant(conditions_str)
        for condition_str in re.split('[;；]', conditions_str):
            condition_str = condition_str.strip()
            if condition_str == '':
                continue
            if condition_str.startswith('$$$') and condition_str.endswith("$$$"):   # $$$$ .... $$$ "
                prompt_template: str = condition_str[3:-3]
                prompt_template = prompt_template.replace('{', '@').replace('}', '@')
                condition_str = f'_check_with_prompt_template("{prompt_template}")'
            elif condition_str.startswith('$') and condition_str.endswith("$"):   # $$$$ .... $$$ "
                task: str = condition_str[1:-1]
                condition_str = f'_check_with_llm("{task}")'
            elif condition_str.startswith('$"') and condition_str[-1] == '"':   # $" .... "
                task: str = condition_str[1:]
                condition_str = f'_check_with_llm({task})'
            else:
                condition_str = self._replace_turn_condition_pattern(condition_str)
                condition_str = self._replace_eq_ne_pattern(condition_str)
            m = function_call_pattern.match(condition_str)  # function pattern match
            if m:
                function_name: str = m.group(1).strip()
                # create argument instances
                argument_list_str: str = m.group(2).strip()
                if argument_list_str:
                    arguments: List[Argument] = [Argument(argument_str.strip()) for argument_str in argument_list_str.split(",")]
                else:
                    arguments = []
                self._conditions.append(Condition(function_name, arguments, condition_str))
            else:
                abort_during_building(f"{condition_str} is not a valid condition.")
        self._actions: List[Action] = []
        actions_str = self.replace_special_characters_in_constant(actions_str)
        for action_str in re.split('[;；]', actions_str):
            action_str = action_str.strip()
            if action_str == "":
                continue
            action_str = self._replace_set_pattern(action_str)
            m = function_call_pattern.match(action_str)
            if m:
                command_name: str = m.group(1).strip()
                argument_list_str: str = m.group(2).strip()
                if argument_list_str:
                    arguments = [Argument(argument_str.strip()) for argument_str in argument_list_str.split(",")]
                else:
                    arguments: List[Argument] = []
                self._actions.append(Action(command_name, arguments, action_str))
            else:
                warn_during_building(f"{action_str} is not a valid action.")
        self._destination: str = destination

    @staticmethod
    def _replace_turn_condition_pattern(condition_str: str) -> str:
        """
        replace num_turns_exceeds syntax sugar (TS>n, TT>n) in condition
        :param condition_str: condition string
        :return: replaced string
        """

        result = condition_str
        m = num_turns_in_state_exceeds_pattern.match(condition_str)
        if m:
            n_str: str = m.group(1)
            n_str = str(int(n_str))  # e.g. "003" -> 3 -> "3"
            result = f'_num_turns_in_state_exceeds("{n_str}")'
        else:
            m = num_turns_exceeds_pattern.match(condition_str)
            if m:
                n_str: str = m.group(1)
                n_str = str(int(n_str))
                result = f'_num_turns_exceeds("{n_str}")'
        return result


    @staticmethod
    def _replace_eq_ne_pattern(condition_str: str) -> str:
        """
        replace eq or ne syntax sugar (aa==bb, aa!=bb) by _eq(aa, bb)/_ne(aa, bb) in condition
        :param condition_str: condition string
        :return: replaced string
        """

        result = condition_str
        m_eq = eq_condition_pattern.match(condition_str)
        if m_eq:
            variable: str = m_eq.group(1)
            if variable[0] == '"':
                abort_during_building("Left-hand side should be a variable: " + condition_str)
            elif variable[0] not in ('#', '*'):
                variable = '*' + variable
            result = f"_eq({variable}, {m_eq.group(2)})"
        else:
            m_ne = ne_condition_pattern.match(condition_str)
            if m_ne:
                variable: str = m_ne.group(1)
                if variable[0] == '"':
                    abort_during_building("Left-hand side should be a variable: " + condition_str)
                elif variable[0] not in ('#', '*'):
                    variable = '*' + variable
                result = f"_ne({variable}, {m_ne.group(2)})"
        return result

    @staticmethod
    def _replace_set_pattern(action_str: str) -> str:
        """
        replace set syntax sugar (a=b) by _set(&a, b) in action
        :param action_str: action string
        :return: replaced string
        """

        result = action_str
        m = set_action_pattern.match(action_str)
        if m:
            result = f"_set(&{m.group(1)}, {m.group(2)})"
        return result

    @staticmethod
    def replace_special_characters_in_constant(string: str):
        """
        replace commas and semicolons in constant (" ..." or { ...})string by special strings
        :param string: input string
        :return: replaced string
        """

        in_constant: bool = False
        result = ""
        for char in string:
            if char == '"':
                in_constant = not in_constant
                result += char
            elif char in (',', '、', '，') and in_constant:
                result += COMMA
            elif char in (';', '；') and in_constant:
                result += SEMICOLON
            elif char == '(' and in_constant:
                result += LEFTPAREN
            elif char == ')' and in_constant:
                result += RIGHTPAREN
            elif char == '"' and in_constant:
                result += DOUBLEQUOTE
            else:
                result += char
        return result

    def get_user_utterance_type(self) -> str:
        """
        returns the user utterance type for this transition
        この遷移のユーザ発話タイプを返す
        :return: user utterance type string
        """
        return self._user_utterance_type

    def get_conditions(self) -> List[Condition]:
        """
        returns the list of conditions for this transition
        この遷移のconditionのリストを返す
        :return: the list of conditions (Condition objects)
        """
        return self._conditions

    def get_actions(self) -> List[Action]:
        """
        returns the list of actions for this transition
        この遷移のactionのリストを返す
        :return: the list of actions (Action objects)
        """
        return self._actions

    def get_destination(self) -> str:
        """
        returns the destination state of this transition
        :return: the name of the destination state
        """
        return self._destination

    def is_default_transition(self) -> bool:
        """
        checks if this is a default transition
        デフォルト遷移かどうかをチェック
        :return: True if this is a default transition
        """
        if self._user_utterance_type or self._conditions:
            return False
        else:
            return True


class State:
    """
    state in state-transition network
    状態遷移ネットワークの状態を表すクラス
    """

    def __init__(self, name: str):
        self._name: str = name  # state name 状態名
        if DEBUG:
            print(f"creating state: {self._name}")
        self._transitions: List[Transition] = []  # transition list 状態のリスト
        self._system_utterances: List[str] = []  # system utterance list システム発話のリスト

        # The number of times system utterances for this state are generated (not managed for each dialogue session)
        # この状態のシステム発話を生成した回数（session毎に管理していない）
        self._system_utterance_generation_count = 0

    def get_name(self):
        """
        returns the name of this state
        この状態の名前を返す
        :return: state name string
        """
        return self._name

    def get_one_system_utterance(self) -> str:
        """
        Returns one system utterance for this state from the candidates.
        When the state has multiple candidates, returns on in turn
        この状態で話すシステム発話を一つ返す
        複数のシステム発話候補がある場合，呼ばれる度にリストの順番に返す
        :return: system utterance string
        """
        num_of_candidates: int = len(self._system_utterances)
        result: str = self._system_utterances[self._system_utterance_generation_count
                                              % num_of_candidates]
        self._system_utterance_generation_count += 1
        return result

    def add_system_utterance(self, utterance: str) -> None:
        """
        register one system utterance to the system utterance list for this state
        システム発話をこの状態に登録
        :param utterance: utterance to add
        """
        utterance = utterance.replace("｛","{")  # zenkaku braces to hankaku
        utterance = utterance.replace("｝","}")  # 全角の中括弧を半角に
        self._system_utterances.append(utterance)

    def add_transition(self, user_utterance_type: str, conditions_str: str,
                       actions_str: str, destination: str) -> None:
        """
        register a transition to this sate
        遷移をこの状態に登録
        :param user_utterance_type: user utterance type ユーザ発話タイプ
        :param conditions_str: conditions in string 条件のリスト（文字列）
        :param actions_str: actions in string アクションのリスト（文字列）
        :param destination: destination state name 遷移する状態の名前
        """
        new_transition = Transition(user_utterance_type, conditions_str, actions_str, destination)
        self._transitions.append(new_transition)

    def get_transitions(self) -> List[Transition]:
        """
        returns the transitions for this state
        この状態の遷移のリストを返す
        :return: the list of transitions (Transition objects)
        """
        return self._transitions

    def get_system_utterances(self) -> List[str]:
        """
        returns the list of system utterance candidates for this state
        この状態で発話されるシステム発話の候補を返す
        :return: the list of system utterance strings
        """
        return self._system_utterances


class StateTransitionNetwork:
    """
    class for representing a state transition network
    状態遷移ネットワークのクラス
    """

    def __init__(self):
        self._error_state = State(ERROR_STATE_NAME)  # error state エラー状態
        self._states = [self._error_state]  # state list 状態のリスト
        self._final_states = []  # list of final states 最終状態のリスト

        # mapping from state names to states 状態名から状態へのマッピング
        self._state_names2states: Dict[str, State] = {ERROR_STATE_NAME: self._error_state}

    def get_state_from_state_name(self, state_name: str) -> State:
        """
        returns the State object having the state_name as the name
        この名前を持つStateオブジェクトを返す
        :param state_name: state name string
        :return: State object having the name
        """
        return self._state_names2states.get(state_name, None)

    def create_new_state(self, state_name: str) -> State:
        """
        creates and returns a new State object having the name
        この名前のStateオブジェクトを作って返す
        :param state_name: state name string
        :return: the created State object
        """
        state: State = State(state_name)
        self._states.append(state)
        if state_name.startswith(FINAL_STATE_PREFIX):  # if it's a final state, register it to the final state list
            self._final_states.append(state)
        self._state_names2states[state_name] = state
        return state

    def is_final_state_or_error_state(self, state_name: str) -> bool:
        """
        if the state having this name is a final state or the error state
        この名前の状態が最終状態かエラー状態か
        :param state_name: 状態名の文字列
        :return: True if it's the case 最終状態かエラー状態ならTrueを返す
        """
        state: State = self._state_names2states[state_name]
        if state is self._error_state:
            return True
        elif state in self._final_states:
            return True
        else:
            return False

    def is_skip_state(self, state_name: str) -> bool:
        """
        judge if a state is a skip state
        :param state_name: the name of a state
        :return: True if it is a skip state, False otherwise
        """
        state: State = self._state_names2states.get(state_name)
        if state and len(state.get_system_utterances()) > 0 and state.get_system_utterances()[0] == SKIP:
            return True
        else:
            return False

    def get_prep_state(self) -> State:
        """
        returns prep state
        prep stateを返す
        :return:  prep state (State object) or None if there's no prep state
        """
        return self._state_names2states.get(PREP_STATE_NAME)

    def check_network(self, repeat_when_no_available_transitions: bool) -> bool:
        """
        checks if network is valid
        このネットワークが正しいか調べる
        :param repeat_when_no_available_transitions: whether repeat the same utterance when there are no available transitions
        :return: True is valid, False otherwise 正しければTrueを返す
        """
        result: bool = True

        # make sure that each state has system utterances
        for state in self._states:
            if state.get_name() != PREP_STATE_NAME and not state.get_system_utterances():
                warn_during_building(f"state '{state.get_name()}' has no system utterances.")
                result = False
            if state == self._error_state or state in self._final_states:
                continue
            else:
                state_name = state.get_name()
                transitions = state.get_transitions()
                if not transitions:
                    warn_during_building(f"state '{state_name}' has no transitions.")
                    result = False
                else:
                    # check default transition
                    has_default_transition: bool = False
                    for transition in transitions:
                        if has_default_transition:
                            warn_during_building(f"state '{state_name}' " +
                                                 " has an extra transition after default transition.")
                        if not transition.get_user_utterance_type() and not transition.get_conditions():
                            has_default_transition = True
                    if not has_default_transition and not repeat_when_no_available_transitions:
                        warn_during_building(f"state '{state_name}' has no default transition.")
        prep_state: State = self._state_names2states.get(PREP_STATE_NAME)
        if prep_state and prep_state.get_system_utterances():
            warn_during_building(f"#prep state must not have system utterances.")

        # check if each destination is a valid state
        all_destinations: List[State] = []
        for state in self._states:
            for transition in state.get_transitions():
                destination_name: str = transition.get_destination()
                if destination_name == EXIT:
                    continue
                elif destination_name.startswith(GOSUB):  # in case of #gosub (sub dialogue)
                    gosub_states: List[str] = re.split('[:：]', destination_name)
                    if len(gosub_states) != 3:
                        warn_during_building(f"gosub description does not have destination and return states: {destination_name}")

                    gosub_destination: str = gosub_states[1].strip()
                    gosub_destination_state: State = self._state_names2states.get(gosub_destination)
                    if not gosub_destination_state:
                        warn_during_building(f"destination {gosub_destination} is not a valid state.")
                    all_destinations.append(gosub_destination_state)

                    gosub_return: str = gosub_states[2].strip()
                    gosub_return_state: State = self._state_names2states.get(gosub_return)
                    if not gosub_return_state:
                        warn_during_building(f"destination {gosub_return} is not a valid state.")
                    all_destinations.append(gosub_return_state)

                else:
                    destination_state: State = self._state_names2states.get(destination_name)
                    if not destination_state:
                        warn_during_building(f"destination {destination_name} is not a valid state.")
                    elif destination_state not in all_destinations:
                        all_destinations.append(destination_state)

        # check if each state is a destination at least one transition
        for state in self._states:
            if state.get_name() in (PREP_STATE_NAME, INITIAL_STATE_NAME,
                                    ERROR_STATE_NAME, FINAL_ABORT_STATE_NAME):
                continue
            if state not in all_destinations:
                warn_during_building(f"state {state.get_name()} is not a destination of any transitions.")
        if not self._state_names2states.get(PREP_STATE_NAME) and not self._state_names2states.get(INITIAL_STATE_NAME):
            warn_during_building(f"either state {INITIAL_STATE_NAME} or state {PREP_STATE_NAME} must exist.")

        # todo check if functions are defined
        # todo check if set command has two args and its first argument is a variable
        return result


















