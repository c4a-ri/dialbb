from flask import Flask, render_template, request, jsonify
import json
from werkzeug.utils import secure_filename
import os
import tkinter as tk
from tkinter import filedialog
from tools.knowledgeConverter2excel import convert2excel
import argparse
import re
from dialbb.no_code.gui_utils import read_gui_text_data, gui_text
from dialbb.builtin_blocks.stn_management.stn_creator import normalize


DOC_ROOT: str = os.path.join(os.path.dirname(os.path.abspath(__file__)))
print(f"template_folder={DOC_ROOT}")
NC_PATH: str = os.path.dirname(os.path.abspath(__file__))
startup_mode = ""

app = Flask(
    __name__, template_folder=DOC_ROOT, static_folder=os.path.join(DOC_ROOT, "static")
)


llm_pattern = re.compile(r"\$\".*?\"")
str_eq_pattern = re.compile(r"(.+?)\s*==\s*(.+)")
str_ne_pattern = re.compile(r"(.+?)\s*!=\s*(.+)")
num_turns_exceeds_pattern = re.compile(r'TT\s*>\s*\d+')  # matches TT><n> such as "TT>3"
num_turns_in_state_exceeds_pattern = re.compile(r'TS\s*>\s*\d+')   #  matches TS><n> e.g. "TS > 4"
num_turns_exceeds_pattern_old = re.compile(r"_num_turns_exceeds\(\s*\"\d+\"\s*\)")
num_turns_in_state_exceeds_pattern_old = re.compile(r"_num_turns_in_state_exceeds\(\s*\"\d+\"\s*\)")


def illegal_condition(condition: str) -> bool:
    """
    check if condition string is illegal or not
    :param condition: condition string
    :return: True if it's illegal
    """
    if (
        llm_pattern.fullmatch(condition)
        or str_eq_pattern.fullmatch(condition)
        or str_ne_pattern.fullmatch(condition)
        or num_turns_exceeds_pattern.fullmatch(condition)
        or num_turns_in_state_exceeds_pattern.fullmatch(condition)
        or num_turns_exceeds_pattern_old.fullmatch(condition)
        or num_turns_in_state_exceeds_pattern_old.fullmatch(condition)
    ):
        return False
    else:
        print("illegal condition: " + condition)
        return True


def check_and_warn(scenario_json_file: str) -> str:
    """
    Check if saved json file is valid as a scenario, and warn otherwise
    :param scenario_json_file: scenario JSON file
    :return warning
    """

    warning: str = ""  # warning message
    initial_node_exists: bool = False
    error_node_exists: bool = False

    with open(scenario_json_file, encoding="utf-8") as fp:
        scenario_json = json.load(fp)

    connect_sources = []
    for connect in scenario_json.get("connects", []):
        connect_sources.append(connect["source"])

    for node in scenario_json.get("nodes", []):
        node_id: str = node["id"]
        if node.get("label") == "userNode":
            conditions: str = node["controls"]["conditions"]["value"].strip()
            conditions = normalize(conditions)  # zenkaku -> hankaku
            if conditions != "":
                for condition in [x.strip() for x in re.split("[;；]", conditions)]:
                    if illegal_condition(condition):
                        warning += (
                            gui_text("msg_warn_user_node_bad_condition")
                            % (node_id, conditions)
                            + "\n"
                        )
            actions = node["controls"]["actions"]["value"].strip()
            actions = normalize(actions)  # zenkaku -> hankaku
            if actions != "":
                warning += (
                    gui_text("msg_warn_user_node_action_note") % (node_id, actions)
                    + "\n"
                )
            if node["id"] not in connect_sources:
                warning += (
                    gui_text("msg_warn_user_node_no_transition_dest") % node_id + "\n"
                )
        elif node.get("label") == "systemNode":
            system_node_type: str = node["controls"]["type"]["value"].strip()
            if system_node_type == "":
                warning += gui_text("msg_warn_sys_node_no_type") % node_id + "\n"
            else:
                if system_node_type == "initial":
                    initial_node_exists = True
                elif system_node_type == "error":
                    error_node_exists = True

                if system_node_type not in ("final", "error"):
                    if node["id"] not in connect_sources:
                        warning += (
                            gui_text("msg_warn_sys_node_no_transition_dest") % node_id
                            + "\n"
                        )

            utterance: str = node["controls"]["utterance"]["value"].strip()
            if utterance == "":
                warning += gui_text("msg_warn_sys_node_utter_empty") % node_id + "\n"

    if not initial_node_exists:
        warning += gui_text("msg_warn_initial_node_exists") + "\n"
    if not error_node_exists:
        warning += gui_text("msg_warn_error_node_exists") + "\n"

    return warning


@app.route("/")
def home():
    return render_template("index.html")


# @app.route('/upload', methods=['POST'])
# def upload_file():
#     print(request)
#     if 'file' not in request.files:
#         return 'No file part'
#     file = request.files['file']
#     if file.filename == '':
#         return 'No selected file'
#     if file:
#         filename = secure_filename(file.filename)
#         file.save(os.path.join(DOC_ROOT, 'static/data/', filename))
#         return 'File successfully uploaded'


@app.route("/save", methods=["POST"])
def save_excel():
    print(request)
    if "file" not in request.files:
        return "No file part"
    file = request.files["file"]
    if file.filename == "":
        return "No selected file"
    if file:
        # 受信データをjsonファイルに保存
        json_file = os.path.join(DOC_ROOT, "data", secure_filename(file.filename))
        print(f"{json_file=}")
        file.save(json_file)
        warning: str = check_and_warn(json_file)
        if startup_mode != "nc":
            # soleの場合はここでExcelへセーブする
            root = tk.Tk()
            root.attributes("-topmost", True)
            root.withdraw()
            # 保存ダイアログ表示
            xlsx_file = filedialog.asksaveasfilename(
                parent=root,
                filetypes=[("Excelファイル", "*.xlsx")],
                defaultextension="xlsx",
            )
            if xlsx_file:
                print(f"file={xlsx_file}")
                # excel変換
                convert2excel(json_file, xlsx_file)
            root.destroy()

        return jsonify({"message": warning})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", type=str, default="nc", help="Startup mode, nc=no code/sole=sole"
    )
    parser.add_argument(
        "--lang",
        choices=["ja", "en"],
        type=str,
        default="ja",
        help="Language type: ja/en",
    )
    args = parser.parse_args()

    # 実行モード
    startup_mode = args.mode
    print(f">>> startup_mode={startup_mode}, lang={args.lang}")

    # GUI表示テキストデータを取得
    read_gui_text_data(os.path.join(NC_PATH, "gui_nc_text.yml"), args.lang)

    # サーバ起動
    # app.debug = True  # リリース時は無効にすること（削除/False）
    app.run(host="localhost")
