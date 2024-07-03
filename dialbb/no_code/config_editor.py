#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# config_editor.py
#   Process of editing config.
#
__version__ = '0.1'
__author__ = 'Mikio Nakano'

import sys
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import ruamel.yaml
from typing import Any, Dict, List


# -------- config.yml編集の管理するクラス -------------------------------------
class config_mng:
    # Search pattern
    serch_pat = {'chatgpt': 'dialbb.builtin_blocks.understanding_with_chatgpt',
                 'spacy': 'dialbb.builtin_blocks.ner_with_spacy'
                 }

    # block data for writing.
    block_chatgpt = {'ja': """name: understander
block_class: dialbb.builtin_blocks.understanding_with_chatgpt.chatgpt_understander.Understander
input:
    input_text: canonicalized_user_utterance
output:
    nlu_result: nlu_result
knowledge_file: nlu-knowledge.xlsx  # 知識記述ファイル
canonicalizer:
    class: dialbb.builtin_blocks.preprocess.japanese_canonicalizer.JapaneseCanonicalizer
""",
                    'en': """name: understander
block_class: dialbb.builtin_blocks.understanding_with_chatgpt.chatgpt_understander.Understander
input:
    input_text: canonicalized_user_utterance
output:
    nlu_result: nlu_result
knowledge_file: nlu-knowledge.xlsx  # knowledge file
canonicalizer:
    class: dialbb.builtin_blocks.preprocess.japanese_canonicalizer.JapaneseCanonicalizer
"""
    }

    block_spacy = {'ja': """name: ner
block_class: dialbb.builtin_blocks.ner_with_spacy.ne_recognizer.SpaCyNER
input:
    input_text: user_utterance
    aux_data: aux_data
output:
    aux_data: aux_data
model: ja_ginza_electra
""",
                    'en': """name: ner
block_class: dialbb.builtin_blocks.ner_with_spacy.ne_recognizer.SpaCyNER
input:
    input_text: user_utterance
    aux_data: aux_data
output:
    aux_data: aux_data
model: en_core_web_trf
"""
    }

    def __init__(self, file_path: str) -> None:
        self.yaml = ruamel.yaml.YAML()
        self.file_path = file_path
        self.yaml.indent(sequence=4, offset=2)
        try:
            with open(file_path, encoding='utf-8') as file:
                self.config = self.yaml.load(file)
        except Exception as e:
            print(f"can't read config file: {file_path}. " + str(e))

        # self.yaml.dump(self.config, sys.stdout)

    # blocksのblock要素を取得
    def get_block(self, name: str) -> Dict[str, str]:
        result = {}
        for block in self.config.get('blocks', ''):
            if block.get('name') == name:
                result = block
                # print(f'block data: {block}')
        return result

    # ChatGPTを利用するかの判定
    def isChatgpt_understander(self) -> bool:
        result = False
        block = self.get_block('understander')
        if self.serch_pat['chatgpt'] in block.get('block_class', ''):
            result = True
        return result

    # spaCyを利用するかの判定
    def isSpacy_ner(self) -> bool:
        result = False
        block = self.get_block('ner')
        if self.serch_pat['spacy'] in block.get('block_class', ''):
            result = True
        return result

    # ChatGPTのmodelを取得
    def get_chatgpt_model(self) -> str:
        result = ''
        chatgpt = self.get_block('manager').get('chatgpt')
        if chatgpt:
            result = chatgpt.get('model')
        return result

    # ChatGPTのsituationを取得
    def get_situation(self) -> List[str]:
        result = ''
        chatgpt = self.get_block('manager').get('chatgpt')
        if chatgpt:
            result = chatgpt.get('situation')
        return '\n'.join(result)

    # ChatGPTのpersonaを取得
    def get_persona(self) -> List[str]:
        result = ''
        chatgpt = self.get_block('manager').get('chatgpt')
        if chatgpt:
            result = chatgpt.get('persona')
        return '\n'.join(result)

    # 書き込みblockデータを得る
    def get_fixed_element(self, class_id: str) -> Any:
        result = ''
        lang = self.config.get('language', '')
        
        if class_id == 'chatgpt':
            result = self.block_chatgpt[lang]
        elif class_id == 'spacy':
            result = self.block_spacy[lang]
        
        return self.yaml.load(result)
    
    # block要素の変更
    def change_block_ele(self, op: str, name: str, class_id: str) -> None:
        find_f = False  # 検出有無

        # 対象nameを検索
        for idx, block in enumerate(self.config.get('blocks', '')):
            if block.get('name') == name:
                find_f = True
                # 追加
                if op == 'add':
                    # 対象classが違う場合は上書き
                    if not self.serch_pat[class_id] in block.get('block_class', ''):
                        # 要素を変更
                        self.config.get('blocks')[idx] = \
                            self.get_fixed_element(class_id)
                # 削除
                elif op == 'del':
                    # 対象classが有れば削除
                    if self.serch_pat[class_id] in block.get('block_class', ''):
                        del self.config.get('blocks')[idx]

        # block要素に対象nameが無く＆追加操作の場合
        if not find_f and op == 'add':
            # 要素を新規追加
            self.config['blocks'].append(self.get_fixed_element(class_id))

        self.yaml.dump(self.config, sys.stdout)

    # ChatGPT blockの編集
    def set_chatgpt_understander(self, kind: str) -> None:
        if kind == 'use':
            self.change_block_ele('add', 'understander', 'chatgpt')
        elif kind == 'unused':
            self.change_block_ele('del', 'understander', 'chatgpt')

    # spaCy blockの編集
    def set_spacy_understander(self, kind: str) -> None:
        if kind == 'use':
            self.change_block_ele('add', 'ner', 'spacy')
        elif kind == 'unused':
            self.change_block_ele('del', 'ner', 'spacy')

    def set_chatgpt_model(self, model: str) -> None:
        chatgpt = self.get_block('manager').get('chatgpt')
        if chatgpt:
            # リストにして空行削除
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
def edit_config(parent, file_path):
    config = config_mng(file_path)

    # 編集画面を表示
    sub_menu = tk.Toplevel(parent)
    sub_menu.title('Edit config')
    sub_menu.grab_set()        # モーダルにする
    sub_menu.focus_set()       # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    parent_x = parent.winfo_rootx() + parent.winfo_width() // 4 - sub_menu.winfo_width() // 2
    parent_y = parent.winfo_rooty() + parent.winfo_height() // 4 - sub_menu.winfo_height() // 2
    sub_menu.geometry(f"400x500+{parent_x}+{parent_y}")

    # Spacy Frameを作成
    sp_frame = ttk.Labelframe(sub_menu, text='spaCy', padding=(10),
                              style='My.TLabelframe')
    sp_frame.pack(side='top', padx=5, pady=5)

    # ［Spacy利用有無］ラジオボタン
    sp_val = tk.StringVar()
    sp_val.set('use' if config.isSpacy_ner() else 'unused')
    sp_rb1 = ttk.Radiobutton(sp_frame, text='used', value='use',
                             variable=sp_val)
    sp_rb2 = ttk.Radiobutton(sp_frame, text='unused', value='unused',
                             variable=sp_val)
    sp_rb1.grid(column=0, row=0, padx=5, pady=5)
    sp_rb2.grid(column=1, row=0, padx=5, pady=5)
    
    # ChatGPT NLU Frameを作成
    gpt_nlu_fr = ttk.Labelframe(sub_menu, text='ChatGPT nlu', padding=(10),
                               style='My.TLabelframe')
    gpt_nlu_fr.pack(expand=True, fill=tk.Y, padx=5, pady=5)

    # ［ChatGPT利用有無］ラジオボタン
    gpt_val = tk.StringVar()
    gpt_val.set('use' if config.isChatgpt_understander() else 'unused')
    gpt_rb1 = ttk.Radiobutton(gpt_nlu_fr, text='use', value='use',
                              variable=gpt_val)
    gpt_rb2 = ttk.Radiobutton(gpt_nlu_fr, text='unused', value='unused',
                              variable=gpt_val)
    gpt_rb1.grid(column=0, row=0, padx=5, pady=5)
    gpt_rb2.grid(column=1, row=0, padx=5, pady=5)

    # ChatGPT Manager Frameを作成
    gpt_mng_fr = ttk.Labelframe(sub_menu, text='ChatGPT manager', padding=(10),
                               style='My.TLabelframe')
    gpt_mng_fr.pack(expand=True, fill=tk.Y, padx=5, pady=5)
    # ［ChatGPTモデル］プルダウンメニュー
    label1 = tk.Label(gpt_mng_fr, text='model:')
    datas = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']
    v = tk.StringVar()
    combobox = ttk.Combobox(gpt_mng_fr, textvariable=v, values=datas,
                            state='normal', style='office.TCombobox')
    # combobox.bind('<<ComboboxSelected>>', select_combo)

    label1.grid(column=0, row=1)
    combobox.grid(column=1, row=1, columnspan=2, padx=5, pady=5)

    # situation入力エリア
    label2 = tk.Label(gpt_mng_fr, text='situation:')
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
    label2 = tk.Label(gpt_mng_fr, text='persona:')
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
    cancel_btn = ttk.Button(sub_menu, text='Cancel',
                            command=lambda: cancel_btn_click())

    # ウィンドウが表示された後に実行される処理を設定
    sub_menu.bind('<Map>', lambda event: on_window_shown())

    # Layout
    sp_frame.pack(fill=tk.X, padx=5, pady=5)
    gpt_nlu_fr.pack(fill=tk.X, padx=5, pady=5)
    gpt_mng_fr.pack(fill=tk.BOTH, padx=5, pady=5)
    cancel_btn.pack(side='right', padx=5, pady=5)
    ok_btn.pack(side='right', padx=5, pady=5)
    # central_position(sub_menu, width=250, height=130)  # サイズ＆表示位置の指定

    # ウィンドウが表示された後にコンボボックスの値を設定する
    def on_window_shown():
        model = config.get_chatgpt_model()
        if model in datas:
            combobox.current(newindex=datas.index(model))

    # ボタンクリックの処理
    def ok_btn_click():
        # ウジェットの設定値を取得
        spacy = sp_val.get()
        chatgpt = gpt_val.get()
        gpt_model = combobox.get()
        situation = stt.get(1.0, tk.END)
        persona = psn.get(1.0, tk.END)

        # cofingデータを変更（差分なくても上書き）
        config.set_chatgpt_understander(chatgpt)
        config.set_spacy_understander(spacy)
        config.set_chatgpt_model(gpt_model)
        config.set_chatgpt_list('situation', situation)
        config.set_chatgpt_list('persona', persona)

        # cofing.yml書き込み
        config.write()

        # 画面を閉じる
        sub_menu.destroy()

    def cancel_btn_click():
        # 画面を閉じる
        sub_menu.destroy()
