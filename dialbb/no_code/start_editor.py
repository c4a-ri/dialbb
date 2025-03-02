import sys

from flask import Flask, render_template, request, jsonify
import json
from werkzeug.utils import secure_filename
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tools.knowledgeConverter2excel import convert2excel
import argparse

DOC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui_editor')
print(f'template_folder={DOC_ROOT}')
startup_mode = ''

app = Flask(__name__,  template_folder=DOC_ROOT,
            static_folder=os.path.join(DOC_ROOT, 'static'))


def check_and_warn(scenario_json_file: str) -> None:
    """
    Check if saved json file is valid as a scenario, and warn otherwise
    :param json_file:
    """

    with open(scenario_json_file, encoding='utf-8') as fp:
        scenario_json = json.load(fp)

    for node in scenario_json.get('nodes', []):
        if node.get('label') == 'userNode':
            actions = node['controls']['actions']['value'].strip()
            if actions != "":
                print(actions)
                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning('Warning',
                                       f'A user node has "{actions}" as actions. Please note that actions are for advanced users.',
                                       detail='Press [OK] to continue.')
                root.mainloop()


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
        check_and_warn(json_file)
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

        return jsonify({'message': ''})


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
