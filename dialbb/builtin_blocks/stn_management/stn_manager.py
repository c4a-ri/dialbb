#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# stn_manager.py
#   perform state transition-based dialogue management
#   状態遷移ネットワークを用いた対話管理

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import copy
from typing import List, Any, Dict, Union
import sys
import os
import importlib
import re
import pandas as pd
from pandas import DataFrame
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import dialbb.main
from dialbb.builtin_blocks.stn_management.scenario_graph import create_scenario_graph
from dialbb.builtin_blocks.stn_management.state_transition_network \
    import StateTransitionNetwork, State, Transition, Argument, Condition, Action, \
    INITIAL_STATE_NAME, ERROR_STATE_NAME, FINAL_ABORT_STATE_NAME
from dialbb.builtin_blocks.stn_management.stn_creator import create_stn
from dialbb.abstract_block import AbstractBlock
from dialbb.main import ANY_FLAG, DEBUG, CONFIG_KEY_FLAGS_TO_USE, CONFIG_DIR
from dialbb.util.error_handlers import abort_during_building

CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET: str = "knowledge_google_sheet"  # google sheet info
CONFIG_KEY_SHEET_ID: str = "sheet_id"  # google sheet id
CONFIG_KEY_KEY_FILE: str = "key_file"  # key file for Google sheets API
CONFIG_KEY_SCENARIO_SHEET: str = "scenario_sheet"
CONFIG_KEY_KNOWLEDGE_FILE: str = "knowledge_file"
CONFIG_KEY_SCENARIO_GRAPH: str = "scenario_graph"
CONFIG_KEY_REPEAT_WHEN_NO_AVAILABLE_TRANSITIONS: str = "repeat_when_no_available_transitions"
CONFIG_KEY_UTTERANCE_TO_ASK_REPETITION: str = "utterance_to_ask_repetition"
CONFIG_KEY_INPUT_CONFIDENCE_THRESHOLD: str = "input_confidence_threshold"
CONFIG_KEY_IGNORE_OOC_BARGE_IN: str = "ignore_out_of_context_barge_in"
CONFIG_KEY_REACTION_TO_SILENCE: str = "reaction_to_silence"
CONFIG_KEY_ACTION: str = "action"
CONFIG_KEY_DESTINATION: str = "destination"

KEY_CURRENT_STATE_NAME: str = "_current_state_name"
KEY_CONFIG: str = "_config"
KEY_BLOCK_CONFIG: str = "_block_config"
KEY_CAUSE: str = "_cause"
KEY_STOP_DIALOGUE: str = "stop_dialogue"
KEY_REWIND: str = 'rewind'
KEY_CONFIDENCE: str = 'confidence'
KEY_BARGE_IN: str = 'barge_in'
KEY_BARGE_IN_IGNORED: str = "barge_in_ignored"
KEY_LONG_SILENCE: str = "long_silence"

SHEET_NAME_SCENARIO: str = "scenario"
DEFAULT_UTTERANCE_ASKING_REPETITION: str = "Could you say that again?"

# builtin function module
# 組み込み関数
BUILTIN_FUNCTION_MODULE: str = "dialbb.builtin_blocks.stn_management.builtin_scenario_functions"

# for using google spreadsheet
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

var_in_system_utterance_pattern = re.compile(r'\{([^\}]+)\}')  # {<variable name>}


class STNError(Exception):
    pass


class Manager(AbstractBlock):
    """
    dialogue management block using state transition network
    状態遷移ネットワークを用いた対話管理ブロック
    """

    def __init__(self, *args):

        super().__init__(*args)

        self._language = self.config.get('language', 'ja')
        # import scenario function definitions
        self._function_modules: List[Any] = []  # list of modules シナリオ関数のモジュールのリスト
        function_definitions: str = self.block_config.get("function_definitions")  # module name(s) in config
        if function_definitions:
            for function_definition in function_definitions.split(':'):
                function_definition_module: str = function_definition.strip()
                imported_module = importlib.import_module(function_definition_module)  # developer specified
                self._function_modules.append(imported_module)
        imported_module = importlib.import_module(BUILTIN_FUNCTION_MODULE)  # builtin
        self._function_modules.append(imported_module)

        # whether to repeat when there are no available transitions (instead of default transition)
        self._repeat_when_no_available_transitions: bool \
            = self.block_config.get(CONFIG_KEY_REPEAT_WHEN_NO_AVAILABLE_TRANSITIONS)

        # set input confidence threshold
        self._input_confidence_threshold = self.block_config.get(CONFIG_KEY_INPUT_CONFIDENCE_THRESHOLD, 0.0)

        # whether to ignore out of context (matching no non-default transition) barge_in
        self._ignore_ooc_barge_in = self.block_config.get(CONFIG_KEY_IGNORE_OOC_BARGE_IN)

        # reaction to long silence
        self._reaction_to_silence: bool = self.block_config.get(CONFIG_KEY_REACTION_TO_SILENCE, False)
        if self._reaction_to_silence:
            self._action_to_react_to_silence: str \
                = self.block_config[CONFIG_KEY_REACTION_TO_SILENCE].get(CONFIG_KEY_ACTION, "")
            if self._action_to_react_to_silence not in ("repeat", "transition"):
                abort_during_building(f"{CONFIG_KEY_REACTION_TO_SILENCE}/{CONFIG_KEY_ACTION}"
                                      + "must be either 'repeat' or 'transition'.")
            elif self._action_to_react_to_silence == "transition":
                self._destination_of_reacting_to_silence \
                    = self.block_config[CONFIG_KEY_REACTION_TO_SILENCE][CONFIG_KEY_DESTINATION]

        # set threshold for asking repetition
        self._ask_repetition_if_confidence_is_low: bool = False
        self._utterance_asking_repetition: str = self.block_config.get(CONFIG_KEY_UTTERANCE_TO_ASK_REPETITION)
        if self._utterance_asking_repetition:
            self._ask_repetition_if_confidence_is_low: bool = True

        # dialogue context for each dialogue session  session id -> {key -> value}
        # セッション毎の対話文脈
        self._dialogue_context: Dict[str, Dict[str, Any]] = {}
        # for rewinding  状態を元に戻す時のため
        self._previous_dialogue_context: Dict[str, Dict[str, Any]] = {}

        # session id -> whether asking repetition or not
        self._asking_repetition: Dict[str, bool] = {}

        # create network
        sheet_name = self.block_config.get(CONFIG_KEY_SCENARIO_SHEET, SHEET_NAME_SCENARIO)
        google_sheet_config: Dict[str, str] = self.block_config.get(CONFIG_KEY_KNOWLEDGE_GOOGLE_SHEET)
        if google_sheet_config:  # google sheet
            scenario_df = self.get_df_from_gs(google_sheet_config, sheet_name)
        else:  # excel
            excel_file = self.block_config.get(CONFIG_KEY_KNOWLEDGE_FILE)
            if not excel_file:
                abort_during_building(
                    f"Neither knowledge file nor google sheet info is not specified for the block {self.name}.")
            scenario_df = self.get_dfs_from_excel(excel_file, sheet_name)
        scenario_df.fillna('', inplace=True)
        flags_to_use = self.block_config.get(CONFIG_KEY_FLAGS_TO_USE, [ANY_FLAG])
        self._network: StateTransitionNetwork = create_stn(scenario_df, flags_to_use)
        if self.block_config.get(CONFIG_KEY_SCENARIO_GRAPH, False):
            create_scenario_graph(scenario_df, CONFIG_DIR) # create graph for scenario writers

        # check network
        if DEBUG:
            self._network.check_network(self._repeat_when_no_available_transitions)

        # generate a graph file from the network
        dot_file: str = os.path.join(CONFIG_DIR, "_stn_graph.dot")  # dot file to input to graphviz
        jpg_file: str = os.path.join(CONFIG_DIR, "_stn_graph.jpg")  # output of graphviz
        self._network.output_graph(dot_file)  # create dot file
        print(f"converting dot file to jpeg: {dot_file}.")
        if self._language == 'ja':
            ret: int = os.system(f'dot -Tjpg -Nfontname="MS Gothic" -Efontname="MS Gothic" '
                                 + f'-Gfontname="MS Gothic" {dot_file} > {jpg_file}')
        else:
            ret: int = os.system(f"dot -Tjpg {dot_file} > {jpg_file}")
        if ret != 0:
            print(f"converting failed. graphviz may not be installed.")

    def get_df_from_gs(self, google_sheet_config: Dict[str, str], scenario_sheet: str) -> DataFrame:
        """
        gets scenario dataframe from google sheet
        シナリオDataFrameをGoogle Sheetから取得
        :param google_sheet_config: configuration for accessing google sheet
        :param scenario_sheet: the name of scenario tab
        :return: pandas DataFrame of scenario
        """

        try:
            google_sheet_id: str = google_sheet_config.get(CONFIG_KEY_SHEET_ID)
            key_file: str = google_sheet_config.get(CONFIG_KEY_KEY_FILE)
            key_file = os.path.join(self.config_dir, key_file)
            credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file, SCOPES)
            gc = gspread.authorize(credentials)
            workbook = gc.open_by_key(google_sheet_id)
            scenario_worksheet = workbook.worksheet(scenario_sheet)
            scenario_data = scenario_worksheet.get_all_values()
            df: DataFrame = pd.DataFrame(scenario_data[1:], columns=scenario_data[0])
            return df
        except Exception as e:
            abort_during_building(f"failed to read google spreadsheet. {str(e)}")

    def get_dfs_from_excel(self, excel_file: str, scenario_sheet: str) -> DataFrame:
        """
        obtains scenario dataframe from an Excel file
        シナリオDataFrameをExcelファイルから取得
        :param excel_file: Excel file
        :param scenario_sheet: scenario sheet name シナリオシート名
        :return: scenario dataframe
        """

        excel_file_path = os.path.join(self.config_dir, excel_file)
        print(f"reading excel file: {excel_file_path}", file=sys.stderr)
        try:
            df_all: Dict[str, DataFrame] = pd.read_excel(excel_file_path, sheet_name=None)  # read all sheets
        except Exception as e:
            abort_during_building(f"failed to read excel file: {excel_file_path}. {str(e)}")
        # reading slots sheet
        return df_all.get(scenario_sheet)

    def _select_nlu_result(self, nlu_results: List[Dict[str,Any]], previous_state_name: str):
        """
        selects nlu result among n-best results that matches one of the transitions.
        if none matches, returns the top result.
        N-best言語理解結果から遷移にマッチするものを選ぶ。どれもマッチしなければトップのものを返す。
        :param nlu_results: n-best nlu_results
        :param previous_state_name: the name of the previous state
        :return: selected nlu result
        """
        previous_state: State = self._network.get_state_from_state_name(previous_state_name)
        for nlu_result in nlu_results:
            uu_type = nlu_result.get("type", "unknown")
            for transition in previous_state.get_transitions():
                if transition.get_user_utterance_type() == uu_type:
                    return nlu_result
        result = nlu_results[0]  # top one
        return result

    def process(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        processes input from dialbb main process and output results to it
        メインプロセスからの入力を受け取って処理結果を返す
        :param input_data: dictionary having the following keys:
                  sentence: canonicalized user utterance string
                  nlu_result: NLU result (dictionary)
                  user id: user id string
                  aux_data: auxiliary data (optional)
        :param session_id: session id string
        :return: dictionary having the following keys
                   output_text: system utterance
                   final: boolean value indicating if the dialogue finished
                   aux_data: dictionary of the form {"state": <current state name>"}
        """

        user_id: str = input_data['user_id']
        nlu_result: Union[Dict[str, Any], List[Dict[str, Any]]] = input_data.get('nlu_result', {"type": "", "slots": {}})
        aux_data: Dict[str, Any] = input_data.get('aux_data')
        if aux_data is None:
            aux_data = {}
        sentence = input_data.get("sentence", "")
        previous_state_name: str = ""

        self._asking_repetition[session_id] = False

        self.log_debug("input: " + str(input_data), session_id=session_id)

        try:
            if not self._dialogue_context.get(session_id):  # first turn 最初のターン
                self._dialogue_context[session_id] = {}
                self._dialogue_context[session_id][KEY_CONFIG] = copy.deepcopy(self.config)
                self._dialogue_context[session_id][KEY_BLOCK_CONFIG] = copy.deepcopy(self.block_config)
                # perform actions in the prep state prep状態のactionを実行する
                prep_state: State = self._network.get_prep_state()
                if prep_state:
                    prep_actions: List[Action] = prep_state.get_transitions()[0].get_actions()
                    if prep_actions:
                        #self._perform_actions(prep_actions, nlu_result, aux_data, user_id, session_id, sentence)
                        # find destination state  遷移先の状態を見つける
                        current_state_name: str = self._transition(prep_state.get_name(), nlu_result, aux_data,
                                                                   user_id, session_id, sentence)
                        self._dialogue_context[session_id][KEY_CURRENT_STATE_NAME] = current_state_name
                else:
                    # move to initial state
                    current_state_name = INITIAL_STATE_NAME
                    self._dialogue_context[session_id][KEY_CURRENT_STATE_NAME] = current_state_name
            else:
                if DEBUG:  # logging for debug
                    dialogue_context: Dict[str, Any] = copy.copy(self._dialogue_context[session_id])
                    del dialogue_context[KEY_CONFIG]  # delete lengthy values
                    del dialogue_context[KEY_BLOCK_CONFIG]
                    self.log_debug("dialogue_context: " + str(dialogue_context), session_id=session_id)

                if aux_data.get(KEY_REWIND):  # revert
                    self.log_debug("Rewinding to the previous dialogue context.")
                    self._dialogue_context[session_id] = self._previous_dialogue_context[session_id]
                else:  # save dialogue context
                    self._previous_dialogue_context[session_id] = copy.deepcopy(self._dialogue_context[session_id])
                previous_state_name = self._dialogue_context[session_id].get(KEY_CURRENT_STATE_NAME, "")
                if previous_state_name == "":
                    self.log_error(f"can't find previous state for session.", session_id=session_id)
                    if DEBUG:
                        raise Exception()
                    else:
                        raise STNError()
                if type(nlu_result) == list:
                    nlu_result = self._select_nlu_result(nlu_result, previous_state_name)
                    self.log_info(f"nlu result selected: {str(nlu_result)}", session_id=session_id)

                #
                if not aux_data.get(KEY_BARGE_IN) and self._ask_repetition_if_confidence_is_low \
                        and aux_data.get(KEY_CONFIDENCE, 1.0) < self._input_confidence_threshold:
                    # repeat
                    self.log_debug("Asking repetition because input confidence is low.")
                    current_state_name: str = previous_state_name
                    self._asking_repetition[session_id] = True
                else:
                    # find destination state  遷移先の状態を見つける
                    current_state_name: str = self._transition(previous_state_name, nlu_result, aux_data,
                                                               user_id, session_id, sentence)
                    self._dialogue_context[session_id][KEY_CURRENT_STATE_NAME] = current_state_name
            new_state: State = self._network.get_state_from_state_name(current_state_name)
            if not new_state:
                # when configured to repeat utterance instead of default transition
                if self._repeat_when_no_available_transitions:
                    self.log_debug("Making no transition since there are no available transitions.")
                    current_state_name: str = previous_state_name
                    new_state = self._network.get_state_from_state_name(current_state_name)
                else:
                    self.log_error(f"can't find state to move.", session_id=session_id)
                    # set cause of the error
                    self._dialogue_context[session_id][KEY_CAUSE] = f"can't find state to move: {current_state_name}"
                    current_state_name = ERROR_STATE_NAME  # move to error state
                    new_state = self._network.get_state_from_state_name(current_state_name)

            # select utterance
            if self._asking_repetition[session_id]:  # when asking repetition
                output_text = self._utterance_asking_repetition
            else:
                output_text = new_state.get_one_system_utterance()
                output_text = self._substitute_variables(output_text, session_id)  # replace variables

            # check if the new state is a final state
            final: bool = False
            if self._network.is_final_state_or_error_state(current_state_name):
                final = True

            aux_data['state'] = current_state_name  # add new state to aux_data

            # create output data
            output = {"output_text": output_text, "final": final, "aux_data": aux_data}

        except STNError as e:
            output = {"output_text": "Internal error occurred.", "final": True}

        self.log_debug("output: " + str(output), session_id=session_id)
        if DEBUG:
            dialogue_context: Dict[str, Any] = copy.copy(self._dialogue_context[session_id])
            del dialogue_context[KEY_CONFIG]
            del dialogue_context[KEY_BLOCK_CONFIG]
            self.log_debug("updated dialogue_context: " + str(dialogue_context), session_id=session_id)
        return output

    def _substitute_variables(self, text: str, session_id: str) -> str:
        """
        replaces variables (in dialogue frame) in the input text with their values
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
                    user_id: str, session_id: str, sentence: str) -> str:
        """
        finds a transition whose conditions are satisfied, performs its actions, and moves to the destination state
        条件が満たされる遷移を見つけてそのアクションを実行し、次の状態に遷移する
        :param previous_state_name: state before transition 遷移前の状態
        :param nlu_result: nlu result
        :param aux_data: auxiliary data received from the main process
        :param user_id: user id string
        :param session_id: session id string
        :return: the name of the destination state to move to 遷移後の状態の名前
        """

        # 今final状態かerror状態か
        # check if the current state is a final or error state
        if self._network.is_final_state_or_error_state(previous_state_name):
            self.log_error("no available transitions found from state: " + previous_state_name,
                           session_id=session_id)
            self._dialogue_context[session_id][KEY_CAUSE] = f"no available transitions found from state: " \
                                                            + previous_state_name
            return ERROR_STATE_NAME

        # if aux data's stop_dialogue value is True, go to #final_abort state
        if aux_data.get(KEY_STOP_DIALOGUE):
            self.log_debug("Moving to #final abort state as requested")
            return FINAL_ABORT_STATE_NAME

        previous_state: State = self._network.get_state_from_state_name(previous_state_name)
        if not previous_state:  # can't find previous state
            self.log_error("can't find previous state: " + previous_state_name, session_id=session_id)
            self._dialogue_context[session_id][KEY_CAUSE] = f"can't find previous state: " + previous_state_name
            return ERROR_STATE_NAME
        self.log_debug("trying to find transition from state: " + previous_state_name)

        # find available transitions 適用可能な遷移を探す
        for transition in previous_state.get_transitions():
            if self._check_transition(transition, nlu_result, aux_data, user_id, session_id, sentence):
                # ignore barge-in out-of-context input
                if self._ignore_ooc_barge_in and aux_data.get(KEY_BARGE_IN, False) \
                        and (transition.is_default_transition()
                             or aux_data.get(KEY_CONFIDENCE) < self._input_confidence_threshold):
                    self.log_debug("Input is barge-in and default transition is selected. Going back to previous sate.")
                    aux_data[KEY_BARGE_IN_IGNORED] = True
                    return previous_state_name

                if self._reaction_to_silence and self._action_to_react_to_silence \
                        and aux_data.get(KEY_LONG_SILENCE, False) \
                        and transition.is_default_transition():
                    if self._action_to_react_to_silence == 'repeat':
                        self.log_debug("Going back to previous state as input is long silence.")
                        return previous_state_name
                    else:  # transition
                        destination_state_name: str = self._destination_of_reacting_to_silence
                        self.log_debug(f"Moving to {destination_state_name} as input is long silence.")
                        return destination_state_name

                destination_state_name: str = transition.get_destination()
                self._perform_actions(transition.get_actions(), nlu_result, aux_data, user_id, session_id, sentence)
                self.log_debug("moving to state: " + destination_state_name, session_id=session_id)
                return destination_state_name



        # when no available transitions 適用可能な遷移がなかった
        if self._repeat_when_no_available_transitions:  # repeat previous utterance
            return previous_state_name

        # judge as an error
        self.log_error("no available transitions found from state: " + previous_state_name,
                       session_id=session_id)
        self._dialogue_context[session_id][KEY_CAUSE] = f"no available transitions found from state: " \
                                                        + previous_state_name
        return ERROR_STATE_NAME

    def _check_one_condition(self, condition: Condition, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                             user_id: str, session_id: str, sentence: str) -> bool:
        """
        checks if the condition is satisfied
        条件が満たされるかどうか調べる
        :param condition:  condition to check
        :param nlu_result: NLU result
        :param aux_data: auxiliary data received from the main process
        :param user_id: user id string
        :param session_id: session id string
        :param sentence: canonicalized user utterance string
        :return: True if the condition is satisfied
        """

        self.log_debug(f"checking condition: {str(condition)}", session_id=session_id)
        function_name: str = condition.get_function()
        condition_function = None

        # search function in function modules  functionをfunction moduleの中で探す
        for function_module in self._function_modules:
            function = getattr(function_module, function_name, None)
            if function:  # if function is found
                condition_function = function
                break
        if not condition_function:  # when condition function is not defined
            self.log_error(f"condition function {function_name} is not defined.", session_id=session_id)
            return False
        else:
            argument_names: List[str] = ["arg" + str(i) for i in range(len(condition.get_arguments()))]
            # realize variables
            argument_values: List[Any] \
                = [self._realize_argument(argument, nlu_result, aux_data, user_id, session_id, sentence)
                   for argument in condition.get_arguments()]
            if DEBUG:
                argument_value_strings: List[str] = [str(x) for x in argument_values]
                self.log_debug(f"condition is realized: {function_name}({','.join(argument_value_strings)})",
                               session_id=session_id)
            argument_names.append("context")  # add context to the arguments 対話文脈を引数に加える
            argument_values.append(self._dialogue_context[session_id])
            args: Dict[str,str] = dict(zip(argument_names, argument_values))
            args["func"] = condition_function
            expression = "func(" + ','.join(argument_names) + ")"
            try:
                result = eval(expression, {}, args)  # evaluate function call 関数呼び出しを評価
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
                          user_id: str, session_id: str, sentence: str) -> bool:
        """
        checks if transition is possible
        遷移が可能か調べる
        :param transition: Transition object to check
        :param nlu_result: NLU result of user input obtained from the understander
        :param user_id: user id
        :param session_id: session id
        :param sentence: canonicalized user utterance string
        :return: True if transition is possible, False otherwise
        """
        uu_type: str = transition.get_user_utterance_type()
        if uu_type != "" and uu_type != nlu_result['type']:
            self.log_debug(f"user utterance type does not match with '{uu_type}'.", session_id=session_id)
            return False
        for condition in transition.get_conditions():
            result = self._check_one_condition(condition, nlu_result, aux_data, user_id, session_id, sentence)
            if not result:
                self.log_debug("transition conditions are not satisfied.", session_id=session_id)
                return False
        self.log_debug(f"transition success", session_id=session_id)
        return True  # all conditions are satisfied

    def _realize_argument(self, argument: Argument, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                          user_id: str, session_id: str, sentence: str) -> str:
        """
        returns the value of an argument of a condition or an action
        引数の値を具体化して返す
        :param argument: Argument object to realize
        :param nlu_result: nlu result
        :param aux_data: auxiliary data received from the main process
        :param user_id: user id string
        :param session_id: session id string
        :param sentence: canonicalized user utterance string
        :return:
        """

        if argument.is_constant():  # quoted string
            return argument.get_name()  # its name as is
        elif argument.is_address():  # starts with '&'
            return argument.get_name()  # its name as is
        elif argument.is_special_variable():  # realize special variable (sentence or slot name)
            slot_name: str = argument.get_name()    # starts with '#'
            if slot_name == "sentence":
                return sentence
            if slot_name == "user_id":
                return user_id
            elif slot_name in nlu_result["slots"].keys():
                return nlu_result["slots"][slot_name]
            elif slot_name in aux_data.keys():
                return aux_data[slot_name]
            else:
                self.log_warning(f"special variable #{str(argument.get_name())} is not realized.", session_id=session_id)
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
                         user_id: str, session_id: str, sentence: str) -> None:
        """
        performs actions in transition
        遷移のactionを実行する
        :param actions: list of actions (Action objects) to perform
        :param nlu_result: nlu result
        :param aux_data: auxiliary data received from the main process
        :param user_id: user id string
        :param session_id: session id string
        :param sentence: canonicalized user utterance string
        """

        for action in actions:
            self.log_debug(f"performing action: {str(action)}", session_id=session_id)
            command_name: str = action.get_function_name()

            # non builtin actions
            action_function = None

            # search action function in function modules
            # action functionをfunction moduleの中から探す
            for function_module in self._function_modules:
                function = getattr(function_module, command_name, None)
                if function is None:  # if command is not in the module
                    continue
                else:
                    action_function = function
                    break
            if not action_function:  # action function is not defined
                self.log_error(f"action function can't find: {command_name}", session_id=session_id)
            else:
                argument_names: List[str] = ["arg" + str(i) for i in range(len(action.get_arguments()))]
                argument_values: List[Any] = [self._realize_argument(argument, nlu_result, aux_data,
                                                                     user_id, session_id, sentence)
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
