import pandas as pd
from pandas import DataFrame
from typing import Dict, List, Any
import argparse
import json, codecs

title = 'NodeエディタのExport(JSON)ファイルを知識記述のExcelに変換する.'


#--------------------
# Typeのシーケンス番号でソートする
#--------------------
def sort_types(df: DataFrame) -> DataFrame:
    df_result = pd.DataFrame()

    # Pickup a list of states
    state_list = df['state'].unique()

    for st in state_list:
        # Sort by type within state
        df_sort = df[df['state'] == st].sort_values(['seqnum'])
        # Delete sequence numbers & Add result dataframe
        df_result = pd.concat([df_result, df_sort.drop(columns='seqnum')])
    
    return df_result


#--------------------
# NodeEditorのJSONをExcelデータ形式に変換
#--------------------
def convert_node2df(json_data: Any) -> DataFrame:
    nodes = []
    sys_node = {}
    
    # Create dict from json
    for node in json_data["nodes"]:
        controls = node["controls"]
        # print(f'label={node["label"]} controls:{controls}')
        row = {}
        if node["label"] == 'systemNode':
            # pickup items of system node
            state = controls["status"]["value"]
            sysutter = controls["utterance"]["value"]
            blank = False
        elif node["label"] == 'userNode':
            # create row data in knowledge excel
            row["flag"] = ""  #"Y"
            row["state"] = state
            row["system utterance"] = sysutter if blank == False else ""
            blank = True
            row["seqnum"] = controls["seqnum"]["value"]
            row["user utterance example"] = controls["utterance"]["value"]
            row["user utterance type"] = controls["type"]["value"]
            row["conditions"] = controls["conditions"]["value"]
            row["actions"] = controls["actions"]["value"]
            row["next state"] = controls["nextStatus"]["value"]

        nodes.append(row)

    # print(nodes)
    return pd.DataFrame(nodes)


#--------------------
#  NodeEditor形式のJSONを知識記述Excelに変換
#--------------------
def convert2excel(json_file: str, exl_file: str):
    # JSON読み込み
    with codecs.open(json_file, 'r', encoding = 'utf_8') as f:
        json_data = json.load(f)
    # print(json_data)

    # NodeEditor形式のJSONをExcelデータに変換
    conv_data = convert_node2df(json_data)

    # Typeのシーケンス番号でソートする
    conv_data = sort_types(conv_data)

    # Write to Excel
    conv_data.to_excel(exl_file, index=False, sheet_name='scenario')
    print('### output excel file {}'.format(exl_file))


if __name__ == "__main__":
    # Set the input parameters.
    parser = argparse.ArgumentParser(description=title)
    parser.add_argument('read_json', type=str, help='read json file.')
    parser.add_argument('save_xl', type=str, help='saved excel file.')
    args = parser.parse_args()

    pd.set_option('display.max_columns', None)

    # Convert
    convert2excel(args.read_json, args.save_xl)
