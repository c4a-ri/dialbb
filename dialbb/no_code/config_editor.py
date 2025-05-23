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
# config_editor.py
#   edit configuration
#   コンフィギュレーションの編集

__version__ = '0.1'
__author__ = 'Mikio Nakano'

import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import ruamel.yaml
from typing import Any, Dict, List

from dialbb.no_code.gui_utils import child_position


# -------- config.yml編集の管理するクラス -------------------------------------
class ConfigManager:

    def __init__(self, file_path: str, template_path: str) -> None:
        self.yaml = ruamel.yaml.YAML()
        self.file_path = file_path
        self.yaml.indent(sequence=4, offset=2)


        try:
            with open(file_path, encoding='utf-8') as file:
                self.config = self.yaml.load(file)
        except Exception as e:
            print(f"can't read config file: {file_path}. " + str(e))

        self.search_pattern = {'understander': 'dialbb.builtin_blocks.understanding_with_chatgpt',
                               'ner': 'dialbb.builtin_blocks.ner_with_chatgpt'}

        # read nlu and ner block descriptions from templates
        self.block_understander: Dict[str, Dict[str, Any]] = {}
        self.block_ner: Dict[str, Dict[str, Any]] = {}
        for language in ('ja', 'en'):
            template_config_file = os.path.join(template_path, language, 'config.yml')
            try:
                with open(template_config_file, encoding='utf-8') as fp:
                    template_config: Dict[str, Any] = self.yaml.load(fp)
            except Exception as e:
                print(f"can't read template config file: {file_path}. " + str(e))
            for block_desc in template_config['blocks']:
                if block_desc['name'] == 'understander':
                    self.block_understander[language] = block_desc
                elif block_desc['name'] == 'ner':
                    self.block_ner[language] = block_desc

        # self.yaml.dump(self.config, sys.stdout)

    # blocksのblock要素を取得
    def get_block(self, name: str) -> Dict[str, Any]:
        result = {}
        for block in self.config.get('blocks', []):
            if block.get('name') == name:
                result = block
                # print(f'### block data: {block}')
        return result

    # whether to use NLUER block
    def if_use_understander(self) -> bool:
        result = False
        block = self.get_block('understander')
        if self.search_pattern['understander'] in block.get('block_class', ''):
            result = True
        return result

    # whether to use NER block
    def if_use_ner(self) -> bool:
        result = False
        block = self.get_block('ner')
        if self.search_pattern['ner'] in block.get('block_class', ''):
            result = True
        return result

    # ChatGPTのmodelを取得
    def get_chatgpt_model(self) -> str:
        result = ''
        # managerのchatgptモデルを参照
        chatgpt = self.get_block('manager').get('chatgpt')
        if chatgpt:
            result = chatgpt.get('model', '')
        return result

    # ChatGPTのsituationを取得
    def get_situation(self) -> str:
        result = ''
        chatgpt: Dict[str, Any] = self.get_block('manager').get('chatgpt')
        if chatgpt:
            result = chatgpt.get('situation')
        return '\n'.join(result)

    # ChatGPTのpersonaを取得
    def get_persona(self) -> str:
        result = ''
        chatgpt: Dict[str, Any] = self.get_block('manager').get('chatgpt')
        if chatgpt:
            result = chatgpt.get('persona')
        return '\n'.join(result)

    # get block descriptions to add
    def get_fixed_element(self, block_name: str) -> Dict[str, Any]:

        lang = self.config.get('language', '')
        
        if block_name == 'understander':
            result: Dict[str, Any] = self.block_understander[lang]
        elif block_name == 'ner':
            result: Dict[str, Any] = self.block_ner[lang]
        else:
            raise Exception("no such block: " + block_name)

        return result
    
    # block要素の変更
    def change_block_ele(self, op: str, name: str) -> None:
        find_f = False  # 検出有無

        # 対象nameを検索
        for idx, block in enumerate(self.config.get('blocks', '')):
            if block.get('name') == name:
                find_f = True
                # 追加
                if op == 'add':
                    # 対象classが違う場合は上書き
                    if not self.search_pattern[name] in block.get('block_class', ''):
                        # 要素を変更
                        self.config.get('blocks')[idx] = \
                            self.get_fixed_element(name)
                # 削除
                elif op == 'del':
                    # 対象classが有れば削除
                    if self.search_pattern[name] in block.get('block_class', ''):
                        del self.config.get('blocks')[idx]

        # block要素に対象nameが無く＆追加操作の場合
        if not find_f and op == 'add':
            # 要素をmanagerの前に追加
            self.config['blocks'].insert(-1, self.get_fixed_element(name))

        self.yaml.dump(self.config, sys.stdout)

    # ChatGPT blockの編集
    def set_chatgpt_understander(self, kind: str) -> None:
        if kind == 'use':
            self.change_block_ele('add', 'understander')
        elif kind == 'not_use':
            self.change_block_ele('del', 'understander')

    # spaCy blockの編集
    def set_spacy_understander(self, kind: str) -> None:
        if kind == 'use':
            self.change_block_ele('add', 'ner')
        elif kind == 'not_use':
            self.change_block_ele('del', 'ner')

    def set_chatgpt_model(self, model: str) -> None:
        if not model:
            return
        # understanderのchatgptモデル設定
        understander = self.get_block('understander')
        if understander:
            understander['model'] = model
        
        # managerのchatgptモデル設定
        chatgpt = self.get_block('manager').get('chatgpt')
        if chatgpt:
            chatgpt['model'] = model

    # situationの設定
    def set_chatgpt_list(self, label: str, data: str) -> None:
        chatgpt = self.get_block('manager').get('chatgpt')
        if chatgpt:
            # リストにして空行削除
            chatgpt[label] = \
                [a for a in data.split('\n') if a != '']

    # config.ymlへ書き込み
    def write(self) -> None:
        with open(self.file_path, mode='w', encoding='utf-8') as file:
            self.yaml.dump(self.config, stream=file)


# Config編集の処理
def edit_config(parent, file_path, template_path, settings):
    config = ConfigManager(file_path, template_path)

    # 編集画面を表示
    sub_menu = tk.Toplevel(parent)
    sub_menu.title('Configuration')
    sub_menu.grab_set()        # モーダルにする
    sub_menu.focus_set()       # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    parent_x = parent.winfo_rootx() + parent.winfo_width() // 4 - sub_menu.winfo_width() // 2
    parent_y = parent.winfo_rooty() + parent.winfo_height() // 10 - sub_menu.winfo_height() // 2
    sub_menu.geometry(f"400x500+{parent_x}+{parent_y}")

    # Spacy Frameを作成
    ner_frame = ttk.Labelframe(sub_menu, text='固有表現抽出を行いますか？', padding=(10),
                               style='My.TLabelframe')
    ner_frame.pack(side='top', padx=5, pady=5)

    # ［Spacy利用有無］ラジオボタン
    sp_val = tk.StringVar()
    sp_val.set('use' if config.if_use_ner() else 'not_use')
    sp_rb1 = ttk.Radiobutton(ner_frame, text='yes', value='use',
                             variable=sp_val)
    sp_rb2 = ttk.Radiobutton(ner_frame, text="no", value='not_use',
                             variable=sp_val)
    sp_rb1.grid(column=0, row=0, padx=5, pady=5)
    sp_rb2.grid(column=1, row=0, padx=5, pady=5)
    
    # NLU Frameを作成
    gpt_nlu_fr = ttk.Labelframe(sub_menu, text='言語理解を行いますか？', padding=(10),
                               style='My.TLabelframe')
    gpt_nlu_fr.pack(expand=True, fill=tk.Y, padx=5, pady=5)

    # ［ChatGPT利用有無］ラジオボタン
    gpt_val = tk.StringVar()
    gpt_val.set('use' if config.if_use_understander() else 'not_use')
    gpt_rb1 = ttk.Radiobutton(gpt_nlu_fr, text='yes', value='use',
                              variable=gpt_val)
    gpt_rb2 = ttk.Radiobutton(gpt_nlu_fr, text="no", value='not_use',
                              variable=gpt_val)
    gpt_rb1.grid(column=0, row=0, padx=5, pady=5)
    gpt_rb2.grid(column=1, row=0, padx=5, pady=5)

    # ChatGPT Manager Frameを作成
    gpt_mng_fr = ttk.Labelframe(sub_menu, text='ChatGPTの設定', padding=(10),
                                style='My.TLabelframe')
    gpt_mng_fr.pack(expand=True, fill=tk.Y, padx=5, pady=5)
    # ［ChatGPTモデル］プルダウンメニュー
    label1 = tk.Label(gpt_mng_fr, text='モデル:')
    models = settings.get_gptmodels()
    if not models:
        # default設定
        models = ['gpt-4o', 'gpt-4o-mini']
    v = tk.StringVar()
    combobox = ttk.Combobox(gpt_mng_fr, textvariable=v, values=models,
                            state='normal', style='office.TCombobox')
    # combobox.bind('<<ComboboxSelected>>', select_combo)

    label1.grid(column=0, row=1)
    combobox.grid(column=1, row=1, columnspan=2, padx=5, pady=5)

    # モデル候補の編集ボタンを追加
    other_model_button = ttk.Button(gpt_mng_fr, text="その他", width=10,
                                    command=lambda: gptmodel_edit(sub_menu, settings))
    other_model_button.grid(column=2, row=1, padx=5)

    # situation入力エリア
    label2 = tk.Label(gpt_mng_fr, text='状況:')
    stt = scrolledtext.ScrolledText(gpt_mng_fr, wrap=tk.NONE, width=24, height=6)
    # 横方向のスクロールバーを作成
    horiz_scrollbar1 = tk.Scrollbar(gpt_mng_fr, orient=tk.HORIZONTAL,
                                    command=stt.xview)
    stt.config(xscrollcommand=horiz_scrollbar1.set)
    # configの値を設定
    stt.insert(0., config.get_situation())
    label2.grid(column=0, row=2)
    stt.grid(column=1, row=2, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
    horiz_scrollbar1.grid(column=1, row=3, columnspan=2, sticky=tk.NSEW)

    # persona入力エリア
    label2 = tk.Label(gpt_mng_fr, text='ペルソナ:')
    psn = scrolledtext.ScrolledText(gpt_mng_fr, wrap=tk.NONE, width=24, height=6)
    # 横方向のスクロールバーを作成
    horiz_scrollbar2 = tk.Scrollbar(gpt_mng_fr, orient=tk.HORIZONTAL,
                                    command=psn.xview)
    psn.config(xscrollcommand=horiz_scrollbar2.set)
    # configの値を設定
    psn.insert(0., config.get_persona())
    # ラベルを作成
    label2.grid(column=0, row=4)
    psn.grid(column=1, row=4, columnspan=2, sticky=tk.NSEW, padx=5, ipady=8)
    horiz_scrollbar2.grid(column=1, row=5, columnspan=2, sticky=tk.NSEW, padx=5)

    gpt_mng_fr.grid_columnconfigure(1, weight=1)
    gpt_mng_fr.grid_rowconfigure(2, weight=1)
    gpt_mng_fr.grid_rowconfigure(4, weight=1)

    # OKボタン
    ok_btn = ttk.Button(sub_menu, text='OK', command=lambda: ok_btn_click())
    # Cancelボタン
    cancel_btn = ttk.Button(sub_menu, text='キャンセル',
                            command=lambda: cancel_btn_click())

    # ウィンドウが表示された後に実行される処理を設定
    sub_menu.bind('<Map>', lambda event: on_window_shown())

    # Layout
    ner_frame.pack(fill=tk.X, padx=5, pady=5)
    gpt_nlu_fr.pack(fill=tk.X, padx=5, pady=5)
    gpt_mng_fr.pack(fill=tk.BOTH, padx=5, pady=5)
    cancel_btn.pack(side='right', padx=5, pady=5)
    ok_btn.pack(side='right', padx=5, pady=5)
    # central_position(sub_menu, width=250, height=130)  # サイズ＆表示位置の指定

    # ウィンドウが表示された後にコンボボックスの値を設定する
    def on_window_shown():
        model = config.get_chatgpt_model()
        if model in models:
            combobox.current(newindex=models.index(model))

    # GPTモデル候補の編集処理
    def gptmodel_edit(parent, settings):
        sub_menu = tk.Toplevel(parent)
        sub_menu.title("GPT models")
        sub_menu.grab_set()        # モーダルにする
        sub_menu.focus_set()       # フォーカスを新しいウィンドウをへ移す
        sub_menu.transient(parent)
        # サイズ＆表示位置の指定
        child_position(parent, sub_menu)

        # GPTモデル候補入力エリア
        label1 = tk.Label(sub_menu, text='Models:')
        mdl = scrolledtext.ScrolledText(sub_menu, wrap=tk.NONE, width=24,
                                        height=6)
        # configの値を設定
        mdl.insert(0., ('\n').join(combobox['values']))

        # Button
        ok_btn = ttk.Button(sub_menu, text='OK', command=lambda: ok_click())
        can_btn = ttk.Button(sub_menu, text="cancel",
                             command=lambda: cancel_click(sub_menu))

        # Layout
        label1.pack(side="left", padx=2, pady=2)
        mdl.pack(padx=1, pady=5)
        can_btn.pack(side="right", padx=5, pady=5)
        ok_btn.pack(side="right", padx=5, pady=5)

        # ボタンクリックされた際のイベント
        def ok_click():
            # プルダウンリストを変更
            in_data = mdl.get(1.0, tk.END)
            models = [a for a in in_data.split('\n') if a != '']
            combobox['values'] = models

            # GPTモデル候補の登録
            settings.set_gptmodels(models)
            # 画面を閉じる
            sub_menu.destroy()

        # [cancel]ボタン：自ウィンドウを閉じる
        def cancel_click(frame):
            # 画面を閉じる
            frame.destroy()

    # ボタンクリックの処理
    def ok_btn_click():
        # ウジェットの設定値を取得
        spacy = sp_val.get()
        chatgpt = gpt_val.get()
        gpt_model = combobox.get()
        situation = stt.get(1.0, tk.END)
        persona = psn.get(1.0, tk.END)

        # change config data (overwrite even if there's no change)
        config.set_chatgpt_understander(chatgpt)
        config.set_spacy_understander(spacy)
        config.set_chatgpt_model(gpt_model)
        config.set_chatgpt_list('situation', situation)
        config.set_chatgpt_list('persona', persona)

        # write config.yml
        config.write()

        # 画面を閉じる
        sub_menu.destroy()
        parent.destroy()

    def cancel_btn_click():
        # 画面を閉じる
        sub_menu.destroy()
        parent.destroy()
