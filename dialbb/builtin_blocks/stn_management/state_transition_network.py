#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# state_transition_network.py
#   classes for representing state transition networks

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import re
from typing import List, Dict
from dialbb.util.error_handlers import abort_during_building, warn_during_building

CONSTANT: str = "constant"
SPECIAL_VARIABLE: str = "special_variable"
VARIABLE: str = "variable"
ADDRESS: str = "address"
INITIAL_STATE_NAME = "#initial"
FINAL_STATE_PREFIX = "#final"
ERROR_STATE_NAME = "#error"
BUILTIN_FUNCTION_PREFIX = "builtin"


class Argument:

    def __init__(self, argument_string: str):
        if argument_string[0] in ('#', '＃'):  # special variable. e.g., slot value #place or #sentence (whole sentence)
            self._type = SPECIAL_VARIABLE
            self._name = argument_string[1:]
        elif argument_string[0] in ('*', '＊'):  # variable value e.g., *aaa
            self._type = VARIABLE
            self._name = argument_string[1:]
        elif argument_string[0] in ('"', '“') and argument_string[-1] in ('"', '”'):  # constant string e.g., "aaaa"
            self._type = CONSTANT
            self._name = argument_string[1:-1]
        elif argument_string[0] in ('&', '＆'):  # variable name
            self._type = ADDRESS
            self._name = argument_string[1:]  # remove '&'
        else:
            warn_during_building("can't create an Argument object: " + argument_string)

    def __str__(self):
        return f"Argument: type={self._type}, name={self._name}"

    def is_special_variable(self) -> bool:
        return self._type == SPECIAL_VARIABLE

    def is_variable(self) -> bool:
        return self._type == VARIABLE

    def is_constant(self) -> bool:
        return self._type == CONSTANT

    def is_address(self) -> bool:
        return self._type == ADDRESS

    def get_name(self) -> str:
        return self._name


class Condition:

    def __init__(self, condition_function: str, arguments: List[Argument], string_representation: str):

        self._condition_function = condition_function
        if condition_function[0] == '_':  # builtin function
            self._condition_function = BUILTIN_FUNCTION_PREFIX + self._condition_function
        self._arguments: List[Argument] = arguments
        self._num_arguments = len(arguments)
        self._string_representation: str = string_representation

    def __str__(self) -> str:
        return self._string_representation

    def get_action_function(self) -> str:
        return self._condition_function

    def get_arguments(self) -> List[Argument]:
        return self._arguments

    def get_num_arguments(self) -> int:
        return self._num_arguments


class Action:

    def __init__(self, command_name: str, arguments: List[Argument], string_representation: str):
        self._command_name: str = command_name
        if command_name[0] == '_':  # builtin function
            self._command_name = BUILTIN_FUNCTION_PREFIX + self._command_name
        self._arguments: List[Argument] = arguments
        self._num_arguments = len(arguments)
        self._string_representation = string_representation

    def __str__(self):
        return self._string_representation

    def get_command_name(self) -> str:
        return self._command_name

    def get_arguments(self) -> List[Argument]:
        return self._arguments

    def get_num_arguments(self) -> int:
        return self._num_arguments


class State:
    """
    state in state-transition network
    """

    def __init__(self, name: str):
        self._name: str = name
        self._transitions: List[Transition] = []
        self._system_utterances: List[str] = []
        self._system_utterance_generation_count = 0

    def get_name(self):
        return self._name

    def get_one_system_utterance(self) -> str:
        num_of_candidates: int = len(self._system_utterances)
        result: str = self._system_utterances[self._system_utterance_generation_count
                                              % num_of_candidates]
        self._system_utterance_generation_count += 1
        return result

    def add_system_utterance(self, utterance: str) -> None:
        self._system_utterances.append(utterance)

    def add_transition(self, user_utterance_type: str, conditions_str: str,
                       actions_str: str, destination: str) -> None:
        new_transition = Transition(user_utterance_type, conditions_str, actions_str, destination)
        self._transitions.append(new_transition)

    def get_transitions(self):
        return self._transitions

    @property
    def get_system_utterances(self):
        return self._system_utterances


function_call_pattern = re.compile("([^(]+)\(([^)]*)\)")  # matches function patter such as "func(..)"


class Transition:

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
        return self._user_utterance_type

    def get_conditions(self) -> List[Condition]:
        return self._conditions

    def get_actions(self) -> List[Action]:
        return self._actions

    def get_destination(self) -> str:
        return self._destination


class StateTransitionNetwork:

    def __init__(self):
        self._initial_state = State(INITIAL_STATE_NAME)
        self._error_state = State(ERROR_STATE_NAME)
        self._states = [self._initial_state, self._error_state]
        self._final_states = []
        self._state_names2states: Dict[str, State] = {INITIAL_STATE_NAME: self._initial_state,
                                                      ERROR_STATE_NAME: self._error_state}

    def get_state_from_state_name(self, state_name: str) -> State:
        return self._state_names2states.get(state_name, None)

    def create_new_state(self, state_name: str) -> State:
        state: State = State(state_name)
        self._states.append(state)
        if state_name.startswith(FINAL_STATE_PREFIX):
            self._final_states.append(state)
        self._state_names2states[state_name] = state
        return state

    def is_final_state_or_error_state(self, state_name: str) -> bool:
        state: State = self._state_names2states[state_name]
        if state is self._error_state:
            return True
        elif state in self._final_states:
            return True
        else:
            return False

    def check_network(self) -> bool:
        """
        check if network is valid
        :return: True is valid, False otherwise
        """
        result: bool = True
        # make sure that special states have system utterances
        for state in self._states:
            if not state.get_system_utterances:
                warn_during_building(f"Special state '{state.get_name()}' has no system utterances.")
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
                            warn_during_building(f"state '{state_name}' has an extra transitions after default transition.")
                        if not transition.get_user_utterance_type() and not transition.get_conditions():
                            has_default_transition = True
                    if not has_default_transition:
                        warn_during_building(f"state '{state_name}' has no default transition.")

        # todo check if functions are defined
        # todo check if set command has two args and its first argument is a variable
        return result

    def output_graph(self, filename: str) -> None:
        """
        output graphviz dot file
        :param filename: filename of the dot file
        """
        result = "digraph state_transition_network {\n"
        result += '  rankdir="TB"\n'
        result += "\n"
        for state in self._states:
            result += f'  "{state.get_name()}" [shape = circle];\n'
        result += "\n"
        for state in self._states:
            for transition in state.get_transitions():
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















