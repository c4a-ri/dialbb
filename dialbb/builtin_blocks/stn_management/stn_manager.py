#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# stn_manager.py
#   perform state transition-based dialogue management

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import copy
from typing import List, Any, Dict
import sys
import os
import importlib
import re

from dialbb.builtin_blocks.stn_management.state_transition_network \
    import StateTransitionNetwork, State, Transition, Argument, Condition, Action, \
    INITIAL_STATE_NAME, FINAL_STATE_PREFIX, ERROR_STATE_NAME
from dialbb.builtin_blocks.stn_management.stn_creator import create_stn
from dialbb.abstract_block import AbstractBlock
from dialbb.main import ANY_FLAG, DEBUG, CONFIG_KEY_FLAGS_TO_USE, KEY_SESSION_ID, CONFIG_DIR


KEY_CURRENT_STATE_NAME: str = "_current_state_name"
KEY_CONFIG: str = "_config"
KEY_BLOCK_CONFIG: str = "_block_config"

CONFIG_KEY_SCENARIO_SHEET: str = "scenario_sheet"
CONFIG_KEY_KNOWLEDGE_FILE: str = "knowledge_file"

SHEET_NAME_SCENARIO: str = "scenario"

BUILTIN_FUNCTION_MODULE: str = "dialbb.builtin_blocks.stn_management.builtin_scenario_functions"

var_in_system_utterance_pattern = re.compile(r'\{([^\}]+)\}')

class STNError(Exception):
    pass


class Manager(AbstractBlock):

    def __init__(self, *args):

        super().__init__(*args)

        self._language = self.config.get('language', 'en')
        # import scenario function definitions
        self._function_modules: List[Any] = []  # list of modules
        function_definitions: str = self.block_config.get("function_definitions")  # module name(s) in config
        if function_definitions:
            for function_definition in function_definitions.split(':'):
                function_definition_module: str = function_definition.strip()
                imported_module = importlib.import_module(function_definition_module)  # developer specified
                self._function_modules.append(imported_module)
        imported_module = importlib.import_module(BUILTIN_FUNCTION_MODULE)  # builtin
        self._function_modules.append(imported_module)
        self._dialogue_context: Dict[str, Dict[str, Any]] = {}  # session id -> {key -> value}

        # create network
        spreadsheet = self.block_config.get(CONFIG_KEY_KNOWLEDGE_FILE)
        if not spreadsheet:
            self._logger.error(f"knowledge_file is not specified for the block {self.name}.")
            sys.exit(1)
        spreadsheet = os.path.join(self.config_dir, spreadsheet)
        sheet_name = self.block_config.get(CONFIG_KEY_SCENARIO_SHEET, SHEET_NAME_SCENARIO)
        flags_to_use = self.block_config.get(CONFIG_KEY_FLAGS_TO_USE, [ANY_FLAG])
        self._network: StateTransitionNetwork = create_stn(spreadsheet, sheet_name, flags_to_use)

        # check network
        self._network.check_network()

        # generate a graph file from the network
        dot_file: str = os.path.join(CONFIG_DIR, "_stn_graph.dot")

        jpg_file: str = os.path.join(CONFIG_DIR, "_stn_graph.jpg")
        self._network.output_graph(dot_file)
        print(f"converting dot file to jpeg: {dot_file}.")
        if self._language == 'ja':
            ret: int = os.system(f'dot -Tjpg -Nfontname="MS Gothic" -Efontname="MS Gothic" -Gfontname="MS Gothic" {dot_file} > {jpg_file}')
        else:
            ret: int = os.system(f"dot -Tjpg {dot_file} > {jpg_file}")
        if ret != 0:
            print(f"converting failed. graphviz may not be installed.")

    def process(self, input: Dict[str, Any], initial: bool = False) -> Dict[str, Any]:
        """
        :param input: key: "sentence"
        :param initial: True if this is the first utterance of the dialogue
        :return: key: "nlu_result"
        """

        session_id: str = input['session_id']
        user_id: str = input['user_id']
        nlu_result: Dict[str, Any] = input.get('nlu_result', {})
        aux_data: Dict[str, Any] = input.get('aux_data', {})

        self.log_debug("input: " + str(input), session_id=session_id)

        if initial:
            self._dialogue_context[session_id] = {}  # initialize dialogue frame
            self._dialogue_context[session_id][KEY_CONFIG] = copy.deepcopy(self.config)
            self._dialogue_context[session_id][KEY_BLOCK_CONFIG] = copy.deepcopy(self.block_config)

        try:
            if initial:
                current_state_name = INITIAL_STATE_NAME
                self._dialogue_context[session_id][KEY_CURRENT_STATE_NAME] = current_state_name
            else:
                previous_state_name: str = self._dialogue_context[session_id][KEY_CURRENT_STATE_NAME]
                if previous_state_name is None:
                    self.log_error(f"can't find previous state for session.", session_id=session_id)
                    if DEBUG:
                        raise Exception()
                    else:
                        raise STNError()
                current_state_name: str = self._transition(previous_state_name, nlu_result, aux_data,
                                                           user_id, session_id)
                self._dialogue_context[session_id][KEY_CURRENT_STATE_NAME] = current_state_name
            current_state: State = self._network.get_state_from_state_name(current_state_name)
            if not current_state:
                self.log_error(f"can't find state to move.", session_id=session_id)
                current_state_name = ERROR_STATE_NAME
                current_state = self._network.get_state_from_state_name(current_state_name)
            output_text = current_state.get_one_system_utterance()
            output_text = self._substitute_variables(output_text, session_id)
            final: bool = False
            if self._network.is_final_state_or_error_state(current_state_name):
                final = True
            output = {"output_text": output_text, "final": final, "aux_data": {"state": current_state_name}}
        except STNError as e:
            output = {"output_text": "Internal error occurred.", "final": True}

        self.log_debug("output: " + str(output), session_id=session_id)
        return output

    def _substitute_variables(self, text: str, session_id: str) -> str:
        """
        replace variables (in dialogue frame) in the input text with their values
        :param text: system utterance with variables
        :return: system utterance whose variables are substituted by their values
        """
        result = text
        for match in var_in_system_utterance_pattern.finditer(result):
            variable = match.group(1)
            if variable in self._dialogue_context[session_id].keys():
                result = result.replace("{" + variable + "}",
                                        self._dialogue_context[session_id][variable])
            else:
                self.log_error(f'variable {variable} in system utterance "{text}" is not found in the dialogue context.')
                if DEBUG:
                    raise Exception()
        return result

    def _transition(self, previous_state_name: str, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                    user_id: str, session_id:str) -> str:
        """
        find a transition whose conditions are satisfied and move to the destination state
        :param previous_state_name:
        :return: id of the destination state to move to
        """
        if self._network.is_final_state_or_error_state(previous_state_name):
            self.log_warning("no available transitions found from state: " + previous_state_name,
                             session_id=session_id)
            return ERROR_STATE_NAME
        previous_state: State = self._network.get_state_from_state_name(previous_state_name)
        if not previous_state:
            return ERROR_STATE_NAME
        self.log_debug("trying to find transition from state: " + previous_state_name)
        for transition in previous_state.get_transitions():
            if self._check_transition(transition, nlu_result, aux_data, user_id, session_id):
                destination_state_name: str = transition.get_destination()
                self._perform_actions(transition.get_actions(), nlu_result, aux_data, user_id, session_id)
                self.log_debug("moving to state: " + destination_state_name, session_id=session_id)
                return destination_state_name
        self.log_warning("no available transitions found from state: " + previous_state_name,
                         session_id=session_id)
        return ERROR_STATE_NAME

    def _check_one_condition(self, condition: Condition, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                             user_id: str, session_id: str) -> bool:
        """
        check if a condition is satisfied
        """
        self.log_debug(f"checking condition: {str(condition)}", session_id=session_id)
        function_name: str = condition.get_action_function()
        condition_function = None
        for function_module in self._function_modules:
            function = getattr(function_module, function_name, None)
            if function is not None:  # if function is not in the module
                condition_function = function
                break
        if not condition_function:
            self.log_error(f"condition function {function_name} is not defined.", session_id=session_id)
            return False
        else:
            argument_names: List[str] = ["arg" + str(i) for i in range(condition.get_num_arguments())]
            # realize variables
            argument_values: List[Any] \
                = [self._realize_argument(argument, nlu_result, aux_data, user_id, session_id)
                   for argument in condition.get_arguments()]
            if DEBUG:
                argument_value_strings: List[str] = [str(x) for x in argument_values]
                self.log_debug(f"condition is realized: {function_name}({','.join(argument_value_strings)})",
                               session_id=session_id)
            argument_names.append("context")  # add context to the arguments
            argument_values.append(self._dialogue_context[session_id])
            args: Dict[str,str] = dict(zip(argument_names, argument_values))
            args["func"] = condition_function
            expression = "func(" + ','.join(argument_names) + ")"
            try:
                result = eval(expression, {}, args)
                if result:
                    self.log_debug(f"condition is satisfied.", session_id=session_id)
                else:
                    self.log_debug(f"condition is not satisfied.", session_id=session_id)
                return result
            except Exception as e:
                self.log_warning(f"Exception occurred during transition {str(condition)}: {str(e)}",
                                 session_id=session_id)
                if DEBUG:
                    raise Exception(e)
                return False  # exception occurred. maybe # of arguments differ

    def _check_transition(self, transition: Transition, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                          user_id: str,
                          session_id: str) -> bool:
        """
        check if transition is possible
        :param transition: Transition object to check
        :param nlu_result: NLU result of user input obtained from the understander
        :param user_id: user id
        :param session_id: session id
        :return: True if transition is possible, False otherwise
        """
        uu_type: str = transition.get_user_utterance_type()
        if uu_type != "" and uu_type != nlu_result['type']:
            self.log_debug(f"user utterance type does not match with '{uu_type}'.", session_id=session_id)
            return False
        for condition in transition.get_conditions():
            result = self._check_one_condition(condition, nlu_result, aux_data, user_id, session_id)
            if not result:
                self.log_debug("transition conditions are not satisfied.", session_id=session_id)
                return False
        self.log_debug(f"transition success", session_id=session_id)
        return True  # all conditions are satisfied

    def _realize_argument(self, argument: Argument, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                          user_id: str, session_id: str) -> str:
        """
        returns the value of an argument of a condition or an action
        :param argument:
        :return: value
        """
        if argument.is_constant():
            return argument.get_name()  # its name as is
        elif argument.is_address():
            return argument.get_name()  # its name as is
        elif argument.is_special_variable():  # realize special variable (sentence or slot name)
            slot_name: str = argument.get_name()
            if slot_name == "sentence":
                return nlu_result["sentence"]
            if slot_name == "user_id":
                return user_id
            elif slot_name in nlu_result["slots"].keys():
                return nlu_result["slots"][slot_name]
            elif slot_name in aux_data.keys():
                return aux_data[slot_name]
            else:
                return slot_name  # do not realize
        elif argument.is_variable():  # realize
            variable_name: str = argument.get_name()
            if variable_name not in self._dialogue_context[session_id]:
                self.log_warning(f"undefined variable: {variable_name}", session_id=session_id)
                return ""
            else:
                value = self._dialogue_context[session_id][variable_name]
                if type(value) != str:
                    self.log_error(f"value of undefined variable: {variable_name}", session_id=session_id)
                else:
                    return value

    def _perform_actions(self, actions: List[Action], nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                         user_id: str, session_id: str) -> None:
        """
        perform actions in transition
        :param actions:
        """
        for action in actions:
            self.log_debug(f"performing action: {str(action)}", session_id=session_id)
            command_name: str = action.get_command_name()

            # non builtin actions
            action_function = None
            for function_module in self._function_modules:
                function = getattr(function_module, command_name, None)
                if function is None:  # if command is not in the module
                    continue
                else:
                    action_function = function
                    break
            if not action_function:
                self.log_error(f"action function can't find: {command_name}", session_id=session_id)
            else:
                argument_names: List[str] = ["arg" + str(i) for i in range(action.get_num_arguments())]
                argument_values: List[Any] = [self._realize_argument(argument, nlu_result, aux_data, user_id, session_id)
                                              for argument in action.get_arguments()]
                if DEBUG:
                    argument_value_strings: List[str] = [str(x) for x in argument_values]
                    self.log_debug(f'action is realized: {command_name}({",".join(argument_value_strings)})',
                                   session_id=session_id)
                argument_names.append("context")
                argument_values.append(self._dialogue_context[session_id])
                args: Dict[str,str] = dict(zip(argument_names, argument_values))
                args["func"] = action_function
                expression = "func(" + ','.join(argument_names) + ")"
                try:
                    eval(expression, {}, args)
                except Exception as e:
                    self.log_warning(f"Exception occurred during performing action {str(action)}: {str(e)}",
                                     session_id=session_id)
                    if DEBUG:
                        raise Exception(e)

