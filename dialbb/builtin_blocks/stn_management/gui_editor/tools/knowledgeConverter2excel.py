import pandas as pd
from pandas import DataFrame
from typing import Dict, List, Any
import argparse
import json
import codecs

title = 'NodeエディタのExport(JSON)ファイルを知識記述のExcelに変換する.'


# --------------------
# Typeのシーケンス番号でソートする
# --------------------
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


# --------------------
# NodeEditorのJSONをExcelデータ形式に変換
# --------------------
def convert_node2df(json_data: Any) -> DataFrame:
    nodes = []
    sys_node = {}
    conn_list = []
    node_list = []
    
    # set connects to DataFrame
    for conn in json_data["connects"]:
        conn_list.append(conn)
    df_conn = pd.DataFrame(conn_list)

    # set nodes to DataFrame
    for node in json_data["nodes"]:
        node_list.append(node)
    df_node = pd.DataFrame(node_list)

    # systemNodeでloop
    for sys_node in df_node[df_node['label'] == 'systemNode'].itertuples():
        # print(f'sys_controls:{sys_node.controls["status"]["value"]}')
        blank = False
        # connectorで繋がっているuserNodeを取得
        for conn in df_conn[df_conn['source'] == sys_node.id].itertuples():
            for user_node in df_node.loc[(df_node['label'] == 'userNode')
                                         & (df_node['id'] == conn.target)].itertuples():
                # print(user_node.controls["utterance"]["value"])

                # create row data for knowledge excel
                row = {}
                row["flag"] = ""  #"Y"
                row["state"] = sys_node.controls["status"]["value"]
                row["system utterance"] = sys_node.controls["utterance"]["value"] \
                    if blank == False else ""
                blank = True
                row["seqnum"] = user_node.controls["seqnum"]["value"]
                row["user utterance example"] = user_node.controls["utterance"]["value"]
                row["user utterance type"] = user_node.controls["type"]["value"]
                row["conditions"] = user_node.controls["conditions"]["value"]
                row["actions"] = user_node.controls["actions"]["value"]
                row["next state"] = user_node.controls["nextStatus"]["value"]
                # Add row data
                nodes.append(row)

    return pd.DataFrame(nodes)


#--------------------
#  NodeEditor形式のJSONを知識記述Excelに変換
#--------------------
def convert2excel(json_file: str, exl_file: str):
    # JSON読み込み
    with codecs.open(json_file, 'r', encoding='utf_8') as f:
        json_data = json.load(f)
    # print(json_data)

    # NodeEditor形式のJSONをExcelデータに変換
    conv_data = convert_node2df(json_data)

    # Typeのシーケンス番号でソートする
    conv_data = sort_types(conv_data)

    # Write to Excel
    conv_data.to_excel(exl_file, index=False, sheet_name='scenario')
    # print('### output excel file {}'.format(exl_file))


if __name__ == "__main__":
    # Set the input parameters.
    parser = argparse.ArgumentParser(description=title)
    parser.add_argument('read_json', type=str, help='read json file.')
    parser.add_argument('save_xl', type=str, help='saved excel file.')
    args = parser.parse_args()

    pd.set_option('display.max_rows', None)    # 行の表示Max
    pd.set_option('display.max_columns', None)  # 列の表示Max

    # Convert
    convert2excel(args.read_json, args.save_xl)
