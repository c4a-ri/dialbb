#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 C4A Research Institute, Inc.
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
# knowledgeConverter2json.py
#   convert a scenario Excel file into a JSON file
#   シナリオExcelファイルをJSONファイルに変換する


import sys
import argparse
import json
import re
import pandas as pd
from pandas import DataFrame
from typing import Dict, List, Set, Any, Tuple

title = "dialbb知識記述のExcelをNodeエディタのImport(JSON)ファイルに変換する."


# --- Class: JSON data format ---
class saveDataForm:
    def __init__(self, nodes: any = None, connects: any = None, types: any = None):
        self.nodes = [] if nodes is None else nodes
        self.connects = [] if connects is None else connects
        self.types = [] if types is None else types


# --- Class: a node format ---
class nodeItem:
    def __init__(
        self,
        label: str = "unknown",
        id: str = "",
        inputs: Any = None,
        outputs: Any = None,
        controls: Any = None,
    ):
        self.label = label
        self.id = id
        self.inputs = {} if inputs is None else inputs
        self.outputs = {} if outputs is None else outputs
        self.controls = {} if controls is None else controls

    def __repr__(self):
        return f"{vars(self)}"


# --- Class: socket connector of a node ---
class connectorItem:
    def __init__(
        self,
        id: str = "",
        sourceOutput: str = "next",
        targetInput: str = "state",
        source: str = "",
        target: str = "",
    ):
        self.id = id
        self.sourceOutput = sourceOutput
        self.targetInput = targetInput
        self.source = source
        self.target = target

    def __repr__(self):
        return f"{vars(self)}"


# --- Class: input control of a node ---
class controlItem:
    def __init__(
        self,
        __type: str = "ClassicPreset.InputControl",
        id: str = "",
        type: str = "text",
        value: str = "",
    ):
        self.__type = __type
        self.id = id
        self.type = type
        self.value = value

    def setValue(self, value):
        self.value = value

    def __repr__(self):
        return f"{vars(self)}"


# --------------------
#  Excel読み込み
# --------------------
def read_excel(exl, sheet=None) -> DataFrame:
    # print('### read_excel start {}'.format(exl))
    try:
        df: DataFrame = pd.read_excel(exl, sheet_name=sheet)
    except Exception as e:
        print(f"failed to read excel file: {exl}. {str(e)}")
        sys.exit(1)

    return df


# --------------------
#  JSONにあるObjectを辞書にシリアライズする
# --------------------
def obj2dict(obj):
    return obj.__dict__


# --------------------
#  次状態→状態へNode接続コネクターを生成
# --------------------
def generate_connectors(nodes: any = None) -> List[connectorItem]:
    print(f"##>>{nodes=}")
    if nodes is None:
        nodes = []
    node_list = []

    # Create Dataframe
    for node in nodes:
        row = {
            "id": node.id,
            "status": node.controls["status"].value,
            "nextSt": node.controls["nextStatus"].value,
        }
        node_list.append(row)
    df = pd.DataFrame(node_list)

    # pd.set_option('display.max_rows', 500)
    # print(df)

    connects = []
    id_cnt = 1

    # pick up nextStatus == status
    for node in nodes:
        nst = node.controls["nextStatus"].value
        pairs = df[df["status"] == nst]
        # print(f'#-- id:{node.id} status={nst} ---#')
        # print(pairs)

        # connects set up
        for idx, row in pairs.iterrows():
            id_cnt += 1
            con = connectorItem(id=id_cnt, source=node.id, target=row["id"])
            connects.append(con)

    return connects


# --------------------
#  状態typeを生成する
# --------------------
def get_state_type(state_types: Set[str], row: Dict[str, str]) -> Tuple[Set[str], str]:
    type = ""
    state = row["state"]
    if re.match("#final", state):
        # finel-xxxは finalに置き換え
        type = "final"
    elif state.startswith("#"):
        # 先頭#を削除してセット
        type = state[1:]
    elif row["system utterance"] == "$skip":
        # system utteranceに$skipが有る場合はskip
        type = "skip"
    else:
        # 他はすべてother
        type = "other"
    state_types.add(type)

    return state_types, type


# --------------------
#  ExcelデータをNodeEditor形式のJSONに変換
# --------------------
def convert_node_data(exl_data: DataFrame) -> Tuple[List[nodeItem], List[str]]:
    nodes = []  # create nodes to return
    state_types = set()  # Array of status types
    cur_state = ""
    con_sys2usr = ""  # connector-id from systemNode to userNode
    exl_data.fillna("", inplace=True)  # Nan -> ''

    print(exl_data[["state", "next state"]])
    # Create controls
    for idx, row in exl_data.iterrows():
        # if row['flag'] != 'Y':
        #     continue
        id = (idx + 1) * 1000

        # status change
        if cur_state != row["state"]:
            # create system node from cell value
            sys_controls = {}
            sys_controls["status"] = controlItem(id=id, value=row["state"])
            id += 1
            sys_controls["utterance"] = controlItem(
                id=id, value=row["system utterance"]
            )
            id += 1

            # 状態typeを生成
            state_types, type = get_state_type(state_types, row)
            sys_controls["type"] = controlItem(id=id, value=type)
            id += 1

            # link of ststus to user node
            con_sys2usr = f"con_sys2usr-{id}"
            sys_controls["nextStatus"] = controlItem(id=id, value=con_sys2usr)
            id += 1

            # Create inputs/outputs
            input = (
                '{ "state": {"id": "'
                + f"{id}"
                + '", "label": "Input", "socket": { "name": "Number" }}}'
            )
            id += 1
            output = (
                '{ "next": {"id": "'
                + f"{id}"
                + '", "label": "Output", "socket": { "name": "Number" }}}'
            )
            id += 1

            # create node
            node_data = nodeItem(
                label="systemNode",
                id=id,
                controls=sys_controls,
                inputs=json.loads(input),
                outputs=json.loads(output),
            )
            id += 1
            nodes.append(node_data)
            cur_state = row["state"]

            # initial number of a user utterance type
            uu_type_num = 100

        # If all data is empty, the user node is not created.
        if "".join(row["user utterance example":"next state"]) == "":
            print("###>user node is not created.")
            continue

        # create user node from cell value
        user_controls = {}
        # link of ststus from system node
        user_controls["status"] = controlItem(id=id, value=con_sys2usr)
        id += 1
        user_controls["utterance"] = controlItem(
            id=id, value=row["user utterance example"]
        )
        id += 1
        user_controls["seqnum"] = controlItem(id=id, value=uu_type_num)
        uu_type_num -= 10  # Add sequence number for type
        id += 1
        # user_controls["type"] = controlItem(id=id, value=f'{uu_type_num}:{row["user utterance type"]}')
        user_controls["type"] = controlItem(id=id, value=row["user utterance type"])
        id += 1
        user_controls["conditions"] = controlItem(id=id, value=row["conditions"])
        id += 1
        user_controls["actions"] = controlItem(id=id, value=row["actions"])
        id += 1
        user_controls["nextStatus"] = controlItem(id=id, value=row["next state"])
        id += 1

        # Create inputs/outputs
        input = (
            '{ "state": {"id": "'
            + f"{id}"
            + '", "label": "Input", "socket": { "name": "Number" }}}'
        )
        id += 1
        output = (
            '{ "next": {"id": "'
            + f"{id}"
            + '", "label": "Output", "socket": { "name": "Number" }}}'
        )
        id += 1

        # Create user Node

        node_data = nodeItem(
            label="userNode",
            id=id,
            controls=user_controls,
            inputs=json.loads(input),
            outputs=json.loads(output),
        )
        id += 1
        nodes.append(node_data)

    #     print(f'node_data : {json.dumps(node_data, default=obj2dict)}')
    # print(f'nodes : {nodes}')
    # print(f'types={state_types}')

    # Return nodes and status type list
    return nodes, list(state_types)


# --------------------
#  ExcelデータをNodeEditor形式のJSONに変換
# --------------------
def convert2json(exl_file: str = "", json_file: str = "init.json"):
    if exl_file:
        # Read Excel
        utterances_df = read_excel(exl_file, "scenario")

        # ExcelデータをNodeEditor形式のJSONに変換
        nodes, uu_types = convert_node_data(utterances_df)

        # Generate connectors between nodes.
        connects = generate_connectors(nodes)

        conv_data = saveDataForm(nodes=nodes, connects=connects, types=uu_types)
    else:
        conv_data = saveDataForm()

    # Convert to JSON
    save_data = vars(conv_data)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, default=obj2dict)


if __name__ == "__main__":
    # Set the input parameters.
    parser = argparse.ArgumentParser(description=title)
    parser.add_argument("read_xl", type=str, help="read excel file.")
    parser.add_argument("save_json", type=str, help="saved json file.")
    args = parser.parse_args()

    # Convert
    convert2json(args.read_xl, args.save_json)
