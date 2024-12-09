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
import pickle
from typing import List, Any, Dict, Union
import sys
import os
import importlib
import re
import pandas as pd
from pandas import DataFrame
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from dialbb.builtin_blocks.stn_management.scenario_graph import create_scenario_graph
from dialbb.builtin_blocks.stn_management.context_db import ContextDB
from dialbb.builtin_blocks.stn_management.state_transition_network \
    import StateTransitionNetwork, State, Transition, Argument, Condition, Action, \
    INITIAL_STATE_NAME, ERROR_STATE_NAME, FINAL_ABORT_STATE_NAME, GOSUB, EXIT, function_call_pattern, \
    BUILTIN_FUNCTION_PREFIX, COMMA, SEMICOLON
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
CONFIG_KEY_CONFIRMATION_REQUEST: str = "confirmation_request"
CONFIG_KEY_INPUT_CONFIDENCE_THRESHOLD: str = "input_confidence_threshold"
CONFIG_KEY_IGNORE_OOC_BARGE_IN: str = "ignore_out_of_context_barge_in"
CONFIG_KEY_REACTION_TO_SILENCE: str = "reaction_to_silence"
CONFIG_KEY_ACTION: str = "action"
CONFIG_KEY_DESTINATION: str = "destination"
CONFIG_KEY_FUNCTION_TO_GENERATE_UTTERANCE: str = "function_to_generate_utterance"
CONFIG_KEY_ACKNOWLEDGEMENT_UTTERANCE_TYPE: str = "acknowledgement_utterance_type"
CONFIG_KEY_DENIAL_UTTERANCE_TYPE: str = "denial_utterance_type"
CONFIG_KEY_CONTEXT_DB: str = "context_db"

CONTEXT_KEY_SAVED_NLU_RESULT: str = "_key_saved_nlu_result"
CONTEXT_KEY_SAVED_AUX_DATA: str = "_key_saved_aux_data"
CONTEXT_KEY_PREVIOUS_SYSTEM_UTTERANCE: str = '_previous_system_utterance'
CONTEXT_KEY_BLOCK_CONFIG: str = "_block_config"
CONTEXT_KEY_AUX_DATA: str = "_aux_data"
CONTEXT_KEY_CAUSE: str = "_cause"
CONTEXT_KEY_CURRENT_STATE_NAME: str = "_current_state_name"
CONTEXT_KEY_CONFIG: str = "_config"
CONTEXT_KEY_DIALOGUE_HISTORY: str = '_dialogue_history'
CONTEXT_KEY_SUB_DIALOGUE_STACK: str = '_sub_dialogue_stack'
CONTEXT_KEY_REACTION: str = '_reaction'
CONTEXT_KEY_REQUESTING_CONFIRMATION: str = '_requesting_confirmation'

INPUT_KEY_AUX_DATA: str = "aux_data"
INPUT_KEY_SENTENCE: str = "sentence"

KEY_STOP_DIALOGUE: str = "stop_dialogue"
KEY_REWIND: str = 'rewind'
KEY_CONFIDENCE: str = 'confidence'
KEY_BARGE_IN: str = 'barge_in'
KEY_BARGE_IN_IGNORED: str = "barge_in_ignored"
KEY_LONG_SILENCE: str = "long_silence"
KEY_TYPE: str = 'type'

SHEET_NAME_SCENARIO: str = "scenario"
DEFAULT_UTTERANCE_ASKING_REPETITION: str = "Could you say that again?"
GENERATION_FAILURE_STRING: str = "..."

# builtin function module
# 組み込み関数
BUILTIN_FUNCTION_MODULE: str = "dialbb.builtin_blocks.stn_management.builtin_scenario_functions"

# for using google spreadsheet
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# {<variable name>||<function call>|<LLM instruction>}
EMBEDDING_PATTERN = re.compile(r'{([^}]+)}')


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
            self._ask_repetition_if_confidence_is_low = True

        # read confirmation request information
        # 確認発話要求に関するコンフィギュレーションの読み込み
        self._request_confirmation_at_low_confidence: bool = False
        confirmation_request_info: Dict[str, str] = self.block_config.get(CONFIG_KEY_CONFIRMATION_REQUEST)
        if confirmation_request_info:
            self._request_confirmation_at_low_confidence = True
            if self._ask_repetition_if_confidence_is_low:
                abort_during_building(f"Cannot specify both '{CONFIG_KEY_CONFIRMATION_REQUEST}' " +
                                      f"and '{CONFIG_KEY_UTTERANCE_TO_ASK_REPETITION}'.")
            self._confirmation_request_generation_function: str \
                = confirmation_request_info.get(CONFIG_KEY_FUNCTION_TO_GENERATE_UTTERANCE)
            if not self._confirmation_request_generation_function:
                abort_during_building(f"confirmation request generation function is not specified.")
            self._confirmation_request_acknowledgement_type: str \
                = confirmation_request_info.get(CONFIG_KEY_ACKNOWLEDGEMENT_UTTERANCE_TYPE)
            if not self._confirmation_request_acknowledgement_type:
                abort_during_building(f"confirmation request acknowledge utterance type is not specified.")
            self._confirmation_request_denial_type: str \
                = confirmation_request_info.get(CONFIG_KEY_DENIAL_UTTERANCE_TYPE)
            if not self._confirmation_request_denial_type:
                abort_during_building(f"confirmation request denial utterance type is not specified.")

        # dialogue context for each dialogue session  session id -> {key -> value}
        # セッション毎の対話文脈
        self._use_context_db: bool = True if self.block_config.get(CONFIG_KEY_CONTEXT_DB) else False
        if self._use_context_db:  # use an external session information database
            self._context_db = ContextDB(self.block_config[CONFIG_KEY_CONTEXT_DB])
        else:
            # session_id -> context
            self._sessions2contexts: Dict[str, Dict[str, Any]] = {}
            # for rewinding  状態を元に戻す時のため
            # session_id -> context
            self._sessions2previous_contexts: Dict[str, bytes] = {}

        # session id -> whether requesting confirmation or not
        #self._requesting_confirmation: Dict[str, bool] = {}
        # session id -> whether asking repetition or not
        #self._asking_repetition: Dict[str, bool] = {}

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

        # check network 状態遷移ネットワークのチェックを行う
        if DEBUG:
            self._network.check_network(self._repeat_when_no_available_transitions)

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

    def _select_nlu_result(self, nlu_results: List[Dict[str,Any]], previous_state_name: str,
                           additional_uu_types: List[str]):
        """
        selects nlu result among n-best results that matches one of the transitions.
        if none matches, returns the top result.
        N-best言語理解結果から遷移にマッチするものを選ぶ。どれもマッチしなければトップのものを返す。
        :param nlu_results: n-best nlu_results
        :param previous_state_name: the name of the previous state
        :param additional_uu_types: the list of additional possible user utterance types
        :return: selected nlu result
        """
        previous_state: State = self._network.get_state_from_state_name(previous_state_name)
        for nlu_result in nlu_results:
            uu_type = nlu_result.get(KEY_TYPE, "unknown")
            for transition in previous_state.get_transitions():
                if transition.get_user_utterance_type() == uu_type:
                    return nlu_result
            if uu_type in additional_uu_types:
                return nlu_result
        result = nlu_results[0]  # return the top one if no transition or additional uu_types matches
        return result

    def _add_context(self, session_id: str, context: Dict[str, Any]) -> None:
        if self._use_context_db:
            self._context_db.add_context(session_id, context)
        else:
            self._sessions2contexts[session_id] = context

    def _get_context(self, session_id: str) -> Dict[str, Any]:
        if self._use_context_db:
            context: Dict[str, Any] = self._context_db.get_context(session_id)
        else:
            context: Dict[str, Any] = self._sessions2contexts.get(session_id)
        return context

    def _add_previous_context(self, session_id: str, context: Dict[str, Any]) -> None:
        if self._use_context_db:
            self._context_db.add_previous_context(session_id, context)
        else:
            self._sessions2previous_contexts[session_id] = pickle.dumps(context)  # unlikely to be used

    def _get_previous_context(self, session_id: str) -> Dict[str, Any]:
        if self._use_context_db:
            context = self._context_db.get_previous_context(session_id)
        else:
            context = pickle.loads(self._sessions2previous_contexts[session_id])
        return context

    def process(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        processes input from dialbb main process and output results to it
        メインプロセスからの入力を受け取って処理結果を返す
        :param input_data: dictionary having the following keys:
                  sentence: canonicalized user utterance string
                  nlu_result: NLU result (dictionary)
                  user id: user id string
                  aux_data: auxiliary data
        :param session_id: session id string
        :return: dictionary having the following keys
                   output_text: system utterance
                   final: boolean value indicating if the dialogue finished
                   aux_data: dictionary of the form {"state": <current state name>"}
        """

        user_id: str = input_data['user_id']
        nlu_result: Union[Dict[str, Any], List[Dict[str, Any]]] = input_data.get('nlu_result', {KEY_TYPE: "", "slots": {}})
        if not nlu_result:
            nlu_result = {KEY_TYPE: "", "slots": {}}
        aux_data: Dict[str, Any] = input_data.get(INPUT_KEY_AUX_DATA)
        if aux_data is None:
            self.log_warning("aux_data is not included in the input", session_id=session_id)
            aux_data = {}
        sentence = input_data.get(INPUT_KEY_SENTENCE, "")
        previous_state_name: str = ""
        new_state_name: str = ""

        asking_repetition = False

        self.log_debug("input: " + str(input_data), session_id=session_id)

        context: Dict[str, Any] = {}

        try:
            context: Dict[str, Any] = self._get_context(session_id)

            if not context:  # first turn in the session

                context = {CONTEXT_KEY_CONFIG: self.config,
                           CONTEXT_KEY_BLOCK_CONFIG: self.block_config,
                           CONTEXT_KEY_AUX_DATA: aux_data,
                           CONTEXT_KEY_DIALOGUE_HISTORY: [],
                           CONTEXT_KEY_SUB_DIALOGUE_STACK: [],
                           CONTEXT_KEY_REACTION: "",
                           CONTEXT_KEY_REQUESTING_CONFIRMATION: False}

                self._add_context(session_id, context)
                self._add_previous_context(session_id, context)

                if type(nlu_result) == list:  # nbest result
                    nlu_result = nlu_result[0]

                # perform actions in the prep state prep状態のactionを実行する
                prep_state: State = self._network.get_prep_state()
                if prep_state:
                    prep_actions: List[Action] = prep_state.get_transitions()[0].get_actions()
                    if prep_actions:  # todo おかしい？
                        #self._perform_actions(prep_actions, nlu_result, aux_data, user_id, session_id, sentence)
                        # find destination state  遷移先の状態を見つける
                        new_state_name: str = self._transition(prep_state.get_name(), nlu_result, aux_data, context,
                                                               user_id, session_id, sentence)
                        new_state_name = self._handle_sub_dialogue(new_state_name, session_id, context)
                        context[CONTEXT_KEY_CURRENT_STATE_NAME] = new_state_name
                else:
                    # move to initial state
                    new_state_name = INITIAL_STATE_NAME
                    context[CONTEXT_KEY_CURRENT_STATE_NAME] = new_state_name
                    self._add_previous_context(session_id, context)
            else:  # non-first turn 2回目以降のターン
                # find previous state
                previous_state_name: str = context.get(CONTEXT_KEY_CURRENT_STATE_NAME, "")

                ### for debug. to delete
                # previous_context = self._get_previous_context(session_id)
                # print(f"for debug: state: {context.get(CONTEXT_KEY_CURRENT_STATE_NAME)}, previous state: {previous_context.get(CONTEXT_KEY_CURRENT_STATE_NAME)}")

                if DEBUG:  # logging for debug
                    self._log_dialogue_context_for_debug(session_id, context)

                if aux_data.get(KEY_REWIND):  # revert
                    context = self._get_previous_context(session_id)
                    rewound_state_name: str = context.get(CONTEXT_KEY_CURRENT_STATE_NAME, "")
                    self.log_debug(f"Rewinding to the previous dialogue context (from {previous_state_name} to {rewound_state_name}).",
                                   session_id=session_id)
                    self._log_dialogue_context_for_debug(session_id, context)
                    previous_state_name = rewound_state_name
                else:  # save dialogue context
                    self._add_previous_context(session_id, context)

                context[CONTEXT_KEY_AUX_DATA] = aux_data

                # update dialogue history
                context[CONTEXT_KEY_DIALOGUE_HISTORY].append({"speaker": "user", "utterance": sentence})

                if previous_state_name == "":
                    self.log_error(f"can't find previous state for session.", session_id=session_id)
                    if DEBUG:
                        raise Exception()
                    else:
                        raise STNError()
                elif self._network.is_final_state_or_error_state(previous_state_name):  # already session finished:
                    self.log_debug("session already finished.")
                    return {"output_text": "This session has already finished.", "final": True, "aux_data": {}}

                if type(nlu_result) == list:   # select nlu result from n-best candidates
                    additional_uu_types = []
                    if self._request_confirmation_at_low_confidence:  # after confirmation request 確認要求後
                        additional_uu_types = [self._confirmation_request_acknowledgement_type,
                                               self._confirmation_request_denial_type]
                    nlu_result = self._select_nlu_result(nlu_result, previous_state_name, additional_uu_types)
                    self.log_info(f"nlu result selected: {str(nlu_result)}", session_id=session_id)

                # when requesting confirmation 確認要求発話の後のユーザ発話の処理
                if context.get(CONTEXT_KEY_REQUESTING_CONFIRMATION):
                    context[CONTEXT_KEY_REQUESTING_CONFIRMATION] = False
                    if aux_data.get(KEY_CONFIDENCE, 1.0) < self._input_confidence_threshold:  # confidence is low
                        new_state_name = previous_state_name  # no transition
                    else:
                        user_utterance_type: str = nlu_result.get(KEY_TYPE, "unknown")
                        if user_utterance_type == self._confirmation_request_acknowledgement_type:
                            self.log_debug("confirmation request is acknowledged.")
                            saved_nlu_result: Dict[str, Any] = context[CONTEXT_KEY_SAVED_NLU_RESULT]
                            saved_aux_data: Dict[str, Any] = context[session_id][CONTEXT_KEY_SAVED_AUX_DATA]
                            context[CONTEXT_KEY_AUX_DATA] = saved_aux_data
                            new_state_name = self._transition(previous_state_name, saved_nlu_result, saved_aux_data,
                                                              context, user_id, session_id, sentence)
                        elif user_utterance_type == self._confirmation_request_denial_type:
                            self.log_debug("confirmation request is denied.")
                            new_state_name = previous_state_name
                        else:
                            new_state_name = self._transition(previous_state_name, nlu_result, aux_data,
                                                              context, user_id, session_id, sentence)

                # request confirmation if confidence is low 確信度が低い時、確認要求を行う
                elif not aux_data.get(KEY_BARGE_IN) and self._request_confirmation_at_low_confidence \
                        and aux_data.get(KEY_CONFIDENCE, 1.0) < self._input_confidence_threshold:

                    # request confirmation
                    self.log_debug("Requesting confirmation because input confidence is low.", session_id=session_id),
                    new_state_name: str = previous_state_name
                    context[CONTEXT_KEY_REQUESTING_CONFIRMATION] = True

                    # saving nlu result to use when user acknowledges confirmation request
                    context[CONTEXT_KEY_SAVED_NLU_RESULT] = nlu_result
                    context[CONTEXT_KEY_SAVED_AUX_DATA] = aux_data

                # ask repetition if confidence is low
                elif not aux_data.get(KEY_BARGE_IN) and self._ask_repetition_if_confidence_is_low \
                        and aux_data.get(KEY_CONFIDENCE, 1.0) < self._input_confidence_threshold:
                    # repeat
                    self.log_debug("Asking repetition because input confidence is low.")
                    new_state_name: str = previous_state_name
                    asking_repetition = True
                else:
                    # find destination state  遷移先の状態を見つける
                    new_state_name: str = self._transition(previous_state_name, nlu_result, aux_data, context,
                                                           user_id, session_id, sentence)
                    new_state_name = self._handle_sub_dialogue(new_state_name, session_id, context)

            # make another transition if new state is a skip state
            if self._network.is_skip_state(new_state_name):
                self.log_debug("Skip state. Making another transition.", session_id=session_id)
                new_state_name = self._transition(new_state_name, nlu_result, aux_data, context,
                                                  user_id, session_id, sentence)

            # when no transition found 遷移がみつからなかった場合
            if new_state_name == "":
                # when configured to repeat utterance instead of default transition
                if self._repeat_when_no_available_transitions:
                    self.log_debug("Making no transition since there are no available transitions.",
                                   session_id=session_id)
                    new_state_name: str = previous_state_name
                    new_state = self._network.get_state_from_state_name(new_state_name)
                else:
                    self.log_error(f"can't find state to move.", session_id=session_id)
                    # set cause of the error
                    context[CONTEXT_KEY_CAUSE] \
                        = f"can't find state to move: {new_state_name}"
                    new_state_name = ERROR_STATE_NAME  # move to error state
                    new_state = self._network.get_state_from_state_name(new_state_name)

            new_state: State = self._network.get_state_from_state_name(new_state_name)

            if not new_state:  # state is not defined 遷移先が定義されていない
                self.log_error(f"State moving to is not defined: " + new_state_name, session_id=session_id)
                # set cause of the error
                context[CONTEXT_KEY_CAUSE] \
                    = f"State moving to is not defined: {new_state_name}"
                new_state_name = ERROR_STATE_NAME  # move to error state
                new_state = self._network.get_state_from_state_name(new_state_name)

            # store the new state for this session
            context[CONTEXT_KEY_CURRENT_STATE_NAME] = new_state_name

            # select utterance システム発話を選択
            if context[CONTEXT_KEY_REQUESTING_CONFIRMATION]:  # when requesting confirmation
                output_text = self._generate_confirmation_request(self._confirmation_request_generation_function,
                                                                  context, nlu_result, session_id)
            elif asking_repetition:  # when asking repetition
                output_text = self._utterance_asking_repetition
            else:
                output_text = new_state.get_one_system_utterance()
                output_text = self._substitute_expressions(output_text, session_id, context, nlu_result,
                                                           aux_data, user_id, sentence)
            # add "_reaction" of dialogue context before output text
            if context[CONTEXT_KEY_REACTION]:
                output_text = f"{context[CONTEXT_KEY_REACTION]} {output_text}"

            context[CONTEXT_KEY_PREVIOUS_SYSTEM_UTTERANCE] = output_text
            context[CONTEXT_KEY_DIALOGUE_HISTORY].append({"speaker": "system", "utterance": output_text})
            context[CONTEXT_KEY_REACTION] = ""

            # check if the new state is a final state
            final: bool = False
            if self._network.is_final_state_or_error_state(new_state_name):
                final = True

            aux_data['state'] = new_state_name  # add new state to aux_data

            # create output data
            output = {"output_text": output_text, "final": final, "aux_data": aux_data}

        except STNError as e:
            output = {"output_text": "Internal error occurred.", "final": True}

        self.log_debug("output: " + str(output), session_id=session_id)
        if DEBUG:
            self._log_dialogue_context_for_debug(session_id, context)

        # store context
        self._add_context(session_id, context)

        return output

    def _log_dialogue_context_for_debug(self, session_id: str, context: Dict[str, Any]):
        dialogue_context: Dict[str, Any] = copy.copy(context)
        del dialogue_context[CONTEXT_KEY_CONFIG]  # delete lengthy values
        del dialogue_context[CONTEXT_KEY_BLOCK_CONFIG]
        del dialogue_context[CONTEXT_KEY_DIALOGUE_HISTORY]
        state: str = dialogue_context[CONTEXT_KEY_CURRENT_STATE_NAME]
        self.log_debug(f"state: {state}, dialogue_context: {str(dialogue_context)}", session_id=session_id)

    def _substitute_expressions(self, text: str, session_id: str, context: Dict[str, Any], nlu_result: Dict[str, Any],
                                aux_data: Dict[str, Any], user_id: str, sentence: str) -> str:
        """
        replaces expressions (variables in dialogue frame or function calls) in the input text with their values
        :param text: system utterance string in the scenario
        :param session_id: session id string
        :param context: context information for this session
        :param nlu_result: nlu results
        :param aux_data: aux_data inputted to the block
        :param user_id: user id string
        :param sentence: input user sentence string
        :return: system utterance in which expressions are realized
        """

        result = Transition.replace_special_characters_in_constant(text)  # replace commas and semicolons in constant

        # variable in context, special variable (starting with '#'), function call,
        # or LLM instruction (starting with !)
        for match in EMBEDDING_PATTERN.finditer(result):
            to_be_replaced: str = match.group(0)
            expression = match.group(1)
            expression = expression.strip()
            if expression.startswith('$'):
                expression = f'_generate_with_llm({expression[1:]})'
            m = function_call_pattern.match(expression)  # matches the function call pattern
            if m:
                function_name: str = m.group(1).strip()
                argument_list_str: str = m.group(2).strip()
                generated_string = self._generate_in_system_utterance(function_name, argument_list_str,
                                                                      nlu_result, aux_data, context, user_id,
                                                                      session_id, sentence)
                result = result.replace(to_be_replaced, generated_string)
            elif expression.startswith('#'):  # realize special variable
                slot_name = expression[1:]
                if slot_name == "sentence":
                    value: str = sentence
                elif slot_name == "user_id":
                    value: str = user_id
                elif slot_name in nlu_result["slots"].keys():
                    value: str = nlu_result["slots"][slot_name]
                elif slot_name in aux_data.keys():
                    value: str = aux_data[slot_name]
                else:
                    self.log_warning(f"special variable #{slot_name} is not realized.", session_id=session_id)
                    value: str = to_be_replaced
                result = result.replace(to_be_replaced, value)
            elif expression in context.keys():
                result = result.replace(to_be_replaced, context[expression])
            else:
                self.log_error(f'variable {expression} in system utterance "{text}" is not found in the dialogue context.')
                if DEBUG:
                    raise Exception()
        return result

    def _handle_sub_dialogue(self, destination_state_string: str, session_id: str, context: Dict[str, Any]) -> str:
        """
        If destination string is sub-dialogue information, return the destination state after stacking the return state,
        Else return as is
        :param destination_state_string:  #gosub:<destination>:<state to return>
        :param session_id: session id string
        :param context: dialogue context information
        :return: destination state name
        """

        if destination_state_string == EXIT:
            print(context[CONTEXT_KEY_SUB_DIALOGUE_STACK])
            destination: str = context[CONTEXT_KEY_SUB_DIALOGUE_STACK].pop()
            self.log_debug("Exiting from sub-dialogue. Returning to: " + destination, session_id=session_id)
            return destination
        elif destination_state_string.startswith(GOSUB):
            states: List[str] = re.split("[:：]", destination_state_string)
            destination: str = states[1].strip()
            state_to_return: str = states[2].strip()
            context[CONTEXT_KEY_SUB_DIALOGUE_STACK].append(state_to_return)
            self.log_debug(f"Entering sub-dialogue at state '{destination}'. "
                           + f"Pushing the return point '{state_to_return}' onto the stack",
                           session_id=session_id)
            return destination
        else:
            return destination_state_string

    def _transition(self, previous_state_name: str, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                    context: Dict[str, Any], user_id: str, session_id: str, sentence: str) -> str:
        """
        finds a transition whose conditions are satisfied, performs its actions, and moves to the destination state
        条件が満たされる遷移を見つけてそのアクションを実行し、次の状態に遷移する
        :param previous_state_name: state before transition 遷移前の状態
        :param nlu_result: nlu result
        :param aux_data: auxiliary data received from the main process
        :param context: dialogue context information
        :param user_id: user id string
        :param session_id: session id string
        :return: the name of the destination state to move to 遷移後の状態の名前
        """

        # 今final状態かerror状態か
        # check if the current state is a final or error state
        if self._network.is_final_state_or_error_state(previous_state_name):
            self.log_error("This session has been ended", session_id=session_id)
            context[CONTEXT_KEY_CAUSE] = "This session no longer exists"
            return ERROR_STATE_NAME

        # if aux data's stop_dialogue value is True, go to #final_abort state
        if aux_data.get(KEY_STOP_DIALOGUE):
            self.log_debug("Moving to #final_abort state as requested", session_id=session_id)
            return FINAL_ABORT_STATE_NAME

        previous_state: State = self._network.get_state_from_state_name(previous_state_name)
        if not previous_state:  # can't find previous state
            self.log_error("can't find previous state: " + previous_state_name, session_id=session_id)
            context[CONTEXT_KEY_CAUSE] = f"can't find previous state: " + previous_state_name
            return ERROR_STATE_NAME
        self.log_debug("trying to find transition from state: " + previous_state_name, session_id=session_id)

        # ignore low-confident barge-in input 確信度の低いバージインは無視
        if self._ignore_ooc_barge_in and aux_data.get(KEY_BARGE_IN, False) \
            and aux_data.get(KEY_CONFIDENCE, 1.0) < self._input_confidence_threshold:
            self.log_debug(f"Input is barge-in and confidence is low. Going back to previous sate.",
                           session_id=session_id)
            aux_data[KEY_BARGE_IN_IGNORED] = True
            return previous_state_name

        # find available transitions 適用可能な遷移を探す
        for transition in previous_state.get_transitions():
            if self._check_transition(transition, nlu_result, aux_data, context, user_id, session_id, sentence):
                # ignore barge-in out-of-context input
                if self._ignore_ooc_barge_in and aux_data.get(KEY_BARGE_IN, False) and transition.is_default_transition():
                    self.log_debug("Input is barge-in and default transition is selected. Going back to previous sate.",
                                   session_id=session_id)
                    aux_data[KEY_BARGE_IN_IGNORED] = True
                    return previous_state_name

                if self._reaction_to_silence and self._action_to_react_to_silence \
                        and aux_data.get(KEY_LONG_SILENCE, False) \
                        and transition.is_default_transition():
                    if self._action_to_react_to_silence == 'repeat':
                        self.log_debug("Going back to previous state as input is long silence.",
                                       session_id=session_id)
                        return previous_state_name
                    else:  # transition
                        destination_state_name: str = self._destination_of_reacting_to_silence
                        self.log_debug(f"Moving to {destination_state_name} as input is long silence.",
                                       session_id=session_id)
                        return destination_state_name

                destination_state_name: str = transition.get_destination()
                self._perform_actions(transition.get_actions(), nlu_result, aux_data, context,
                                      user_id, session_id, sentence)
                self.log_debug("moving to state: " + destination_state_name, session_id=session_id)

                return destination_state_name

        # when no available transitions 適用可能な遷移がなかった
        if self._repeat_when_no_available_transitions:  # repeat previous utterance
            return previous_state_name

        # judge as an error
        self.log_error("no available transitions found from state: " + previous_state_name,
                       session_id=session_id)
        context[CONTEXT_KEY_CAUSE] = f"no available transitions found from state: " \
                                                                + previous_state_name
        return ERROR_STATE_NAME

    def _search_function_in_modules(self, function_name: str):
        """
        search function in function modules  functionをfunction moduleの中で探す
        :param function_name: name of the function to search
        :return: function object or None if no such function is found
        """
        for function_module in self._function_modules:
            function = getattr(function_module, function_name, None)
            if function:  # if function is found
                return function
        return None

    def _generate_in_system_utterance(self, function_name: str, argument_list_string: str,
                                      nlu_result: Dict[str, Any], aux_data: Dict[str, Any], context: Dict[str, Any],
                                      user_id: str, session_id: str, sentence: str) -> str:
        """
        generate string by calling function in system utterance
        システム発話中の関数呼び出し
        :param function_name: name of function
        :param argument_list_string: string of arguments (the string in the parenthesis). can be an empty string
        :param nlu_result: NLU result
        :param aux_data: auxiliary data received from the main process
        :param context: dialogue context information
        :param user_id: user id string
        :param session_id: session id string
        :param sentence: canonicalized user utterance string
        :return: True if the condition is satisfied
        """

        if function_name[0] == '_':  # when builtin
            function_name = BUILTIN_FUNCTION_PREFIX + function_name

        argument_names: List[str] = []
        if argument_list_string:
            # replace commas and semicolons in constant strings
            argument_names= [argument_str.strip().replace(COMMA, ',').replace(SEMICOLON,"")
                             for argument_str in re.split("[,，、]", argument_list_string)]

        self.log_debug(f"calling function in system utterance: {function_name}({argument_list_string})",
                       session_id=session_id)

        generation_function = self._search_function_in_modules(function_name)

        if not generation_function:  # when condition function is not defined
            self.log_error(f"generation function {function_name} is not defined.", session_id=session_id)
            return GENERATION_FAILURE_STRING

        # realize variables 変数の具体化
        try:
            argument_values: List[Any] \
                = [self._realize_argument(Argument(argument), nlu_result, aux_data, context,
                                          user_id, session_id, sentence)
                   for argument in argument_names]
        except Exception as e:  # failure in realization
            self.log_warning(f"Exception occurred during realizing arguments in system utterance: {str(argument_names)}",
                             session_id=session_id)
            if DEBUG:
                raise Exception(e)
            return GENERATION_FAILURE_STRING
        if DEBUG:  # print details
            argument_value_strings: List[str] = [str(x) for x in argument_values]
            self.log_debug(f"function call in system utterance is realized: {function_name}({','.join(argument_value_strings)})",
                           session_id=session_id)
        argument_names.append("context")  # add context to the arguments 対話文脈を引数に加える
        argument_values.append(context)
        args: Dict[str, str] = dict(zip(argument_names, argument_values))
        args["func"] = generation_function
        expression = "func(" + ','.join(argument_names) + ")"
        try:
            result = eval(expression, {}, args)  # evaluate function call 関数呼び出しを評価
            self.log_debug(f"generated in system utterance: {result}", session_id=session_id)
            return result
        except Exception as e:
            self.log_warning(f"Exception occurred during system generation in utterance: {str(function_name)}: {str(e)}",
                             session_id=session_id)
            if DEBUG:
                raise Exception(e)
            return GENERATION_FAILURE_STRING

    def _check_one_condition(self, condition: Condition, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                             context: Dict[str, Any], user_id: str, session_id: str, sentence: str) -> bool:
        """
        checks if the condition is satisfied
        条件が満たされるかどうか調べる
        :param condition:  condition to check
        :param nlu_result: NLU result
        :param aux_data: auxiliary data received from the main process
        :param context: dialogue context information
        :param user_id: user id string
        :param session_id: session id string
        :param sentence: canonicalized user utterance string
        :return: True if the condition is satisfied
        """

        self.log_debug(f"checking condition: {str(condition)}", session_id=session_id)
        function_name: str = condition.get_function()
        condition_function = self._search_function_in_modules(function_name)
        if not condition_function:  # when condition function is not defined
            self.log_error(f"condition function {function_name} is not defined.", session_id=session_id)
            return False
        else:
            argument_names: List[str] = ["arg" + str(i) for i in range(len(condition.get_arguments()))]
            # realize variables 変数の具体化
            argument_values: List[Any] \
                = [self._realize_argument(argument, nlu_result, aux_data, context,
                                          user_id, session_id, sentence)
                   for argument in condition.get_arguments()]
            if DEBUG:
                argument_value_strings: List[str] = [str(x) for x in argument_values]
                self.log_debug(f"condition is realized: {function_name}({','.join(argument_value_strings)})",
                               session_id=session_id)
            argument_names.append("context")  # add context to the arguments 対話文脈を引数に加える
            argument_values.append(context)
            args: Dict[str, str] = dict(zip(argument_names, argument_values))
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
                self.log_warning(f"Exception occurred during checking condition {str(condition)}: {str(e)}",
                                 session_id=session_id)
                if DEBUG:
                    raise Exception(e)
                return False  # exception occurred. maybe # of arguments differ

    def _check_transition(self, transition: Transition, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                          context: Dict[str, Any], user_id: str, session_id: str, sentence: str) -> bool:
        """
        checks if transition is possible
        遷移が可能か調べる
        :param transition: Transition object to check
        :param nlu_result: NLU result of user input obtained from the understander
        :param aux_data: auxiliary data received from the main process
        :param context: dialogue context information
        :param user_id: user id
        :param session_id: session id
        :param sentence: canonicalized user utterance string
        :return: True if transition is possible, False otherwise
        """
        uu_type: str = transition.get_user_utterance_type()
        if uu_type != "" and uu_type != nlu_result[KEY_TYPE]:
            self.log_debug(f"user utterance type does not match with '{uu_type}'.", session_id=session_id)
            return False
        for condition in transition.get_conditions():
            result = self._check_one_condition(condition, nlu_result, aux_data, context, user_id, session_id, sentence)
            if not result:
                self.log_debug("transition conditions are not satisfied.", session_id=session_id)
                return False
        self.log_debug(f"transition success", session_id=session_id)
        return True  # all conditions are satisfied

    def _realize_argument(self, argument: Argument, nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                          context: Dict[str, Any], user_id: str, session_id: str, sentence: str) -> str:
        """
        returns the value of an argument of a condition or an action
        引数の値を具体化して返す
        :param argument: Argument object to realize
        :param nlu_result: nlu result
        :param aux_data: auxiliary data received from the main process
        :param context: dialogue context information
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
                self.log_warning(f"special variable #{str(argument.get_name())} is not realized.",
                                 session_id=session_id)
                return ""  # do not realize
        elif argument.is_variable():  # realize
            variable_name: str = argument.get_name()
            if variable_name not in context:
                self.log_warning(f"undefined variable: {variable_name}", session_id=session_id)
                return ""
            else:
                value = context[variable_name]
                if type(value) != str:
                    self.log_error(f"value of undefined variable: {variable_name}", session_id=session_id)
                else:
                    return value

    def _perform_actions(self, actions: List[Action], nlu_result: Dict[str, Any], aux_data: Dict[str, Any],
                         context: Dict[str, Any], user_id: str, session_id: str, sentence: str) -> None:
        """
        performs actions in transition
        遷移のactionを実行する
        :param actions: list of actions (Action objects) to perform
        :param nlu_result: nlu result
        :param aux_data: auxiliary data received from the main process
        :param context: dialogue context information
        :param user_id: user id string
        :param session_id: session id string
        :param sentence: canonicalized user utterance string
        """

        for action in actions:
            self.log_debug(f"performing action: {str(action)}", session_id=session_id)
            command_name: str = action.get_function_name()

            # realize action
            action_function = self._search_function_in_modules(command_name)
            if not action_function:  # action function is not defined
                self.log_error(f"can't find action function: {command_name}", session_id=session_id)
            else:
                argument_names: List[str] = ["arg" + str(i) for i in range(len(action.get_arguments()))]
                argument_values: List[Any] = [self._realize_argument(argument, nlu_result, aux_data, context,
                                                                     user_id, session_id, sentence)
                                              for argument in action.get_arguments()]
                if DEBUG:
                    argument_value_strings: List[str] = [str(x) for x in argument_values]
                    self.log_debug(f'action is realized: {command_name}({",".join(argument_value_strings)})',
                                   session_id=session_id)
                argument_names.append("context")
                argument_values.append(context)
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

    def _generate_confirmation_request(self, function_name: str, context: Dict[str, Any],
                                       nlu_result: Dict[str, Any], session_id: str) -> str:

        self.log_debug(f"generating confirmation request: {str(function_name)}", session_id=session_id)

        # search confirmation request function in function modules
        # confirmation request functionをfunction moduleの中から探す
        generation_function = None
        for function_module in self._function_modules:
            function = getattr(function_module, function_name, None)
            if function is None:  # if command is not in the module
                continue
            else:
                generation_function = function
                break
        if not generation_function:  # action function is not defined
            self.log_error(f"can't find confirmation request function: {function_name}", session_id=session_id)
        else:
            argument_names: List[str] = ["nlu_result", "context"]
            argument_values: List[Any] = [nlu_result, context]
            args: Dict[str,str] = dict(zip(argument_names, argument_values))
            args["func"] = generation_function
            expression = "func(" + ','.join(argument_names) + ")"
            result = ""
            try:
                result: str = eval(expression, {}, args)
            except Exception as e:
                self.log_warning(f"Exception occurred during generating confirmation request " +
                                 f"{str(generation_function)}: {str(e)}",
                                 session_id=session_id)
                if DEBUG:
                    raise Exception(e)
            return result

