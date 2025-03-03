

from flask import Flask, render_template, request, jsonify
import json
from werkzeug.utils import secure_filename
import os
import tkinter as tk
from tkinter import filedialog
from tools.knowledgeConverter2excel import convert2excel
import argparse
import re

DOC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui_editor')
print(f'template_folder={DOC_ROOT}')
startup_mode = ''

app = Flask(__name__,  template_folder=DOC_ROOT,
            static_folder=os.path.join(DOC_ROOT, 'static'))


llm_pattern = re.compile(r'\$\".*?\"')
str_eq_pattern = re.compile(r'(.+?)\s*==\s*(.+)')
str_ne_pattern = re.compile(r'(.+?)\s*!=\s*(.+)')
num_turns_exceeds_pattern = re.compile(r'_num_turns_exceeds\(\s*\"\d+\"\s*\)')


def illegal_condition(condition: str) -> bool:
    """
    check if condition string is illegal or not
    :param condition: condition string
    :return: True if it's illegal
    """
    if llm_pattern.fullmatch(condition) \
            or str_eq_pattern.fullmatch(condition) \
            or str_ne_pattern.fullmatch(condition) \
            or num_turns_exceeds_pattern.fullmatch(condition):
        return False
    else:
        return True


def check_and_warn(scenario_json_file: str) -> str:
    """
    Check if saved json file is valid as a scenario, and warn otherwise
    :param scenario_json_file: scenario JSON file
    :return warning
    """

    warning = ""

    with open(scenario_json_file, encoding='utf-8') as fp:
        scenario_json = json.load(fp)

    for node in scenario_json.get('nodes', []):
        if node.get('label') == 'userNode':
            conditions: str = node['controls']['conditions']['value'].strip()
            if conditions != "":
                for condition in [x.strip() for x in re.split('[;；]', conditions)]:
                    if illegal_condition(condition):
                        warning += f'Warning: ユーザノードの遷移の条件"{condition}"は正しい条件ではありません。\n'
            actions = node['controls']['actions']['value'].strip()
            if actions != "":
                warning += f'Warning: ユーザノードの遷移時のアクションに"{actions}"が書かれています。遷移時のアクションは上級者向けのものであることに注意して下さい。\n'
        elif node.get('label') == 'systemNode':
            utterance: str = node['controls']['utterance']['value'].strip()
            if utterance == "":
                warning += f'Warning: utteranceが空のシステムノードがあります。\n'
    return warning

@app.route('/')
def home():
    return render_template('index.html')


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


@app.route('/save', methods=['POST'])
def save_excel():
    print(request)
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        # 受信データをjsonファイルに保存
        json_file = os.path.join(DOC_ROOT, 'static/data/',
                                 secure_filename(file.filename))
        file.save(json_file)
        warning: str = check_and_warn(json_file)
        if startup_mode != 'nc':
            # soleの場合はここでExcelへセーブする
            root = tk.Tk()
            root.attributes('-topmost', True)
            root.withdraw()
            # 保存ダイアログ表示
            xlsx_file = filedialog.asksaveasfilename(
                parent=root,
                filetypes=[('Excelファイル', '*.xlsx')],
                defaultextension='xlsx')
            if xlsx_file:
                print(f'file={xlsx_file}')
                # excel変換
                convert2excel(json_file, xlsx_file)
            root.destroy()

        return jsonify({'message': warning})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str, default='nc', help="Startup mode, nc=no code/sole=sole")
    args = parser.parse_args()

    # 実行モード
    startup_mode = args.mode
    print(f'>>> startup_mode={startup_mode}')

    # サーバ起動
    app.debug = True
    app.run(host='localhost')
