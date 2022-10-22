#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# scenario_graph.py
#   create graph for scenario writer (not based on system)

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import os

from pandas import DataFrame
from typing import Dict, Any, List

from dialbb.builtin_blocks.stn_management.stn_creator import COLUMN_STATE, COLUMN_SYSTEM_UTTERANCE, \
    COLUMN_DESTINATION, COLUMN_USER_UTTERANCE_EXAMPLE
import dataclasses


@dataclasses.dataclass
class TransitionForGraph:
    user_utterance_example: str
    next_state: str


@dataclasses.dataclass
class StateForGraph:
    transitions: List[TransitionForGraph]
    system_utterances: List[str]


def create_scenario_graph(scenario_df: DataFrame, config_dir: str, language: str='ja') -> None:
    """
    create scenario graph file from scenario dataframe
    :param scenario_df: scenario dataframe
    :param config_dir: configuration dir
    :return: None
    """

    dot_file: str = os.path.join(config_dir, "_scenario_graph.dot")
    jpg_file: str = os.path.join(config_dir, "_scenario_graph.jpg")
    states_dict: Dict[str, StateForGraph] = {}

    for index, row in scenario_df.iterrows():
        current_state_name = row[COLUMN_STATE]
        if current_state_name == "":
            print(f"'state' column is empty at row {str(index + 1)}.")
            continue
        current_state: StateForGraph = states_dict.get(current_state_name)
        if not current_state:
            current_state = StateForGraph([], [])
            states_dict[current_state_name] = current_state
        system_utterance = row[COLUMN_SYSTEM_UTTERANCE]
        if system_utterance != "":
            current_state.system_utterances.append(system_utterance)
        if row[COLUMN_DESTINATION]:
            transition = TransitionForGraph(row[COLUMN_USER_UTTERANCE_EXAMPLE], row[COLUMN_DESTINATION])
            current_state.transitions.append(transition)

    result = "digraph scenario_graph {\n"
    result += '  rankdir="TB"\n'
    result += "\n"
    for state_name, state in states_dict.items():
        su_list = ""
        for su in state.system_utterances:
            su_list += "\\n"
            su_list += su
        su_label = ""
        i = 0
        while i < len(su_list):  # new line at every 10 char
            su_label += su_list[i:i+10] + "\\n"
            i += 10
        result += f'  "{state_name}" [shape = circle, label="<{state_name}>\\n{su_label}"];\n'
    result += "\n"
    for state_name, state in states_dict.items():
        for transition in state.transitions:
            uu: str = transition.user_utterance_example
            if uu:
                result += f'  "{state_name}" -> "{transition.next_state}" [label = "{uu}" ] ;\n'
            else:
                result += f'  "{state_name}" -> "{transition.next_state}" ;\n'
    result += "}"

    with open(dot_file, "w", encoding='utf-8') as fp:
        fp.write(result)
    print(f"converting dot file to jpeg: {dot_file}.")
    if language == 'ja':
        ret: int = os.system(f'dot -Tjpg -Nfontname="MS Gothic" -Efontname="MS Gothic" -Gfontname="MS Gothic" {dot_file} > {jpg_file}')
    else:
        ret: int = os.system(f"dot -Tjpg {dot_file} > {jpg_file}")
    if ret != 0:
        print(f"converting failed. graphviz may not be installed.")


