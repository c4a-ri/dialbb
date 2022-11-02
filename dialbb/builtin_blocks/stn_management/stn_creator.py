#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# stn_creator.py
#   creates a state transition network from spreadsheet description

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import sys

from pandas import DataFrame
from typing import List

from dialbb.builtin_blocks.stn_management.state_transition_network import StateTransitionNetwork, State
from dialbb.main import ANY_FLAG
from dialbb.util.error_handlers import abort_during_building, warn_during_building

COLUMN_FLAG: str = "flag"
COLUMN_STATE: str = "state"
COLUMN_SYSTEM_UTTERANCE: str = "system utterance"
COLUMN_USER_UTTERANCE_EXAMPLE = "user utterance example"
COLUMN_USER_UTTERANCE_TYPE: str = "user utterance type"
COLUMN_CONDITIONS: str = "conditions"
COLUMN_ACTIONS: str = "actions"
COLUMN_DESTINATION: str = "next state"


def create_stn(df: DataFrame, flags_to_use: List[str]) -> StateTransitionNetwork:


    # check column names
    columns = df.columns.values.tolist()
    for required_column in [COLUMN_STATE, COLUMN_FLAG, COLUMN_SYSTEM_UTTERANCE, COLUMN_USER_UTTERANCE_TYPE,
                            COLUMN_CONDITIONS, COLUMN_ACTIONS, COLUMN_DESTINATION]:
        if required_column not in columns:
            print(f"Column '{required_column}' is missing in the scenario sheet. "
                  + "There might be extra whitespaces.", file=sys.stderr)
            sys.exit(1)

    stn: StateTransitionNetwork = StateTransitionNetwork()

    for index, row in df.iterrows():
        if row[COLUMN_FLAG] not in flags_to_use and ANY_FLAG not in flags_to_use:
            continue  # ignore the row
        current_state_name = row[COLUMN_STATE]
        if current_state_name == "":
            warn_during_building(f"'state' column is empty at row {str(index + 1)}.")
            continue
        current_state: State = stn.get_state_from_state_name(current_state_name)
        if current_state is None:
            current_state = stn.create_new_state(current_state_name)
        system_utterance = row[COLUMN_SYSTEM_UTTERANCE]
        if system_utterance != "":
            current_state.add_system_utterance(system_utterance)
        if row[COLUMN_DESTINATION]:
            current_state.add_transition(row[COLUMN_USER_UTTERANCE_TYPE], row[COLUMN_CONDITIONS],
                                         row[COLUMN_ACTIONS], row[COLUMN_DESTINATION])
        elif row[COLUMN_USER_UTTERANCE_TYPE] or row[COLUMN_CONDITIONS] or row[COLUMN_ACTIONS]:
            warn_during_building(f"empty destination with non-empty conditions or actions at row {str(index + 1)}")

    return stn
