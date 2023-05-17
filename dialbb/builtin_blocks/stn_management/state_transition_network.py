#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

CONSTANT: str = "constant"
SPECIAL_VARIABLE: str = "special_variable"
VARIABLE: str = "variable"
ADDRESS: str = "address"
PREP_STATE_NAME = "#prep"
INITIAL_STATE_NAME = "#initial"
FINAL_STATE_PREFIX = "#final"
ERROR_STATE_NAME = "#error"
BUILTIN_FUNCTION_PREFIX = "builtin"


class Argument:
    """
    Argument of scenario functions
    シナリオ関数の引数を表すクラス
    """

    def __init__(self, argument_string: str):

        if argument_string[0] in ('#', '＃'): # special variable 特殊変数
            self._type = SPECIAL_VARIABLE
            self._name = argument_string[1:]
        elif argument_string[0] in ('*', '＊'):  # variable value e.g., *aaa 変数の値
            self._type = VARIABLE
            self._name = argument_string[1:]
        elif argument_string[0] in ('"', '“') and argument_string[-1] in ('"', '”'):  # constant string 定数文字列
            self._type = CONSTANT
            self._name = argument_string[1:-1]
        elif argument_string[0] in ('&', '＆'):  # variable name 変数名
            self._type = ADDRESS
            self._name = argument_string[1:]  # remove '&'
        else:
            warn_during_building("can't create an Argument object: " + argument_string)

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
    a condition for state transition
    状態遷移の条件を表すクラス
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
        self._user_utterance_type: str = user_utterance_type.strip()
        self._conditions: List[Condition] = []
        for condition_str in conditions_str.split(';'):
            condition_str = condition_str.strip()
            if condition_str == '':
                continue
            m = function_call_pattern.match(condition_str)  # function pattern match
            if m:
                function_name = m.group(1).strip()
                # create argument instances
                arguments = [Argument(argument_str.strip()) for argument_str in m.group(2).split(",")]
                self._conditions.append(Condition(function_name, arguments, condition_str))
            else:
                abort_during_building(f"{condition_str} is not a valid condition.")
        self._actions: List[Action] = []
        for action_str in actions_str.split(';'):
            action_str = action_str.strip()
            if action_str == "":
                continue
            m = function_call_pattern.match(action_str)
            if m:
                command_name = m.group(1).strip()
                argument_list_str = m.group(2).strip()
                if argument_list_str:
                    arguments = [Argument(argument_str.strip()) for argument_str in argument_list_str.split(",")]
                else:
                    arguments = []
                self._actions.append(Action(command_name, arguments, action_str))
            else:
                warn_during_building(f"{action_str} is not a valid action.")
        self._destination: str = destination

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


class State:
    """
    state in state-transition network
    状態遷移ネットワークの状態を表すクラス
    """

    def __init__(self, name: str):
        self._name: str = name  # state name 状態名
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


function_call_pattern = re.compile("([^(]+)\(([^)]*)\)") # matches function patter such as "func(..)"


class StateTransitionNetwork:
    """
    class for representing a state transition network
    状態遷移ネットワークのクラス
    """

    def __init__(self):
        self._initial_state = State(INITIAL_STATE_NAME)  # initial state 初期状態
        self._error_state = State(ERROR_STATE_NAME)  # error state エラー状態
        self._states = [self._initial_state, self._error_state]  # state list 状態のリスト
        self._final_states = []  # list of final states 最終状態のリスト

        # mapping from state names to states 状態名から状態へのマッピング
        self._state_names2states: Dict[str, State] = {INITIAL_STATE_NAME: self._initial_state,
                                                      ERROR_STATE_NAME: self._error_state}

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
        # make sure that special states have system utterances
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
                    if not has_default_transition and repeat_when_no_available_transitions:
                        warn_during_building(f"state '{state_name}' has no default transition.")
        prep_state: State = self._state_names2states.get(PREP_STATE_NAME)
        if prep_state:
            if len(prep_state.get_transitions()) != 1:
                warn_during_building(f"#prep state must have one transition.")
            elif prep_state.get_transitions()[0].get_destination() != INITIAL_STATE_NAME:
                warn_during_building(f"the destination of the #prep state's transition must be #initial.")
            elif prep_state.get_transitions()[0].get_user_utterance_type():
                warn_during_building(f"#prep state's transition must not have user utterance type.")
            elif prep_state.get_transitions()[0].get_conditions():
                warn_during_building(f"#prep state's transition must not have conditions.")
            elif prep_state.get_system_utterances():
                warn_during_building(f"#prep state must not have system utterances.")

        # check if each destination is a valid state
        all_destinations: List[State] = []
        for state in self._states:
            for transition in state.get_transitions():
                destination_name: str = transition.get_destination()
                destination_state = self._state_names2states.get(destination_name)
                if not destination_state:
                    warn_during_building(f"destination {destination_name} is not a valid state.")
                elif destination_state not in all_destinations:
                    all_destinations.append(destination_state)
        # check if each state is a destination at least one transition
        for state in self._states:
            if state.get_name() in (PREP_STATE_NAME, INITIAL_STATE_NAME, ERROR_STATE_NAME):
                continue
            if state not in all_destinations:
                warn_during_building(f"state {state.get_name()} is not a destination of any transitions.")

        # todo check if functions are defined
        # todo check if set command has two args and its first argument is a variable
        return result

    def output_graph(self, filename: str) -> None:
        """
        output graphviz dot file for this network
        このネットワークのgraphvizのdot fileを作成する
        :param filename: filename of the dot file
        """
        result = "digraph state_transition_network {\n"
        result += '  rankdir="TB"\n'
        result += "\n"
        for state in self._states:
            result += f'  "{state.get_name()}" [shape = circle];\n'
        result += "\n"
        n_trans: int = 0
        for state in self._states:
            for transition in state.get_transitions():
                n_trans += 1
                label = ""
                uutype: str = transition.get_user_utterance_type()
                if uutype:
                    label += f"uu_type: {uutype}"
                conditions = ','.join([str(condition).replace('"', '\\"') for condition in transition.get_conditions()])
                if conditions:
                    if label:
                        label += "\\n"
                    label += f"conditions: {conditions}"
                actions = ','.join([str(action).replace('"', '\\"') for action in transition.get_actions()])
                if actions:
                    if label:
                        label += "\\n"
                    label += f"actions: {actions}"
                if label:
                    result += f'  "{state.get_name()}" -> "{transition.get_destination()}" [label = "{label}" ] ;\n'
                else:
                    result += f'  "{state.get_name()}" -> "{transition.get_destination()}" ;\n'
        result += "}"

        with open(filename, "w", encoding='utf-8') as fp:
            fp.write(result)

        print(f"state transition network has {len(self._states)} states.")
        print(f"state transition network has {n_trans} transitions.")
















