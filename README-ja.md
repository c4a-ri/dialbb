# DialBB: 対話システム構築フレームワーク


ver. 1.0.0

[English](README.md)

## プロジェクトWebサイト

[プロジェクトのメインWebサイト](https://c4a-ri.github.io/dialbb/index-ja.html)に，DialBBの概要，
詳細な仕様を記述したドキュメント，チュートリアルスライド，ノーコードツールのドキュメントなどがあります．

## ドキュメント

詳細な仕様やアプリケーションの構築法は[ドキュメント](https://c4a-ri.github.io/dialbb/document-ja/build/html/)を参照して下さい．

## 引用

DialBBを用いた研究に関する論文発表をする際には，以下の論文の引用をお願いします．

- Mikio Nakano and Kazunori Komatani. [DialBB: A Dialogue System Development Framework as an Educational Material](https://aclanthology.org/2024.sigdial-1.56). In Proceedings of the 25th Annual Meeting of the Special Interest Group on Discourse and Dialogue (SIGDIAL-24), pages 664–668, Kyoto, Japan. Association for Computational Linguistics, 2024.

## ライセンス

DialBBはApache License 2.0の下で公開されています．

## サンプルアプリケーションの起動の仕方

### 実行環境

Ubuntu 20.04/Windows 10上のpython 3.10.13で，以下の手順で動作することを確認しています．すべての組み合わせを完全に確かめたわけではありませんが，Windows 10/11やMacOS（アップルシリコンを含む）の上で，Python 3.10+を使って動かせなかったという報告は得ていません．

以下の説明はUbuntu上のbashで作業することを仮定しています．他のシェルやWindowsコマンドプロンプトを用いる場合は，適宜読み替えてください．

### DialBBのインストール

- 必要なら仮想環境を構築します．以下はvenvの例です．

  ```sh
  $ python -m venv venv  # 仮想環境をvenvという名前で構築
  $ venv/bin/activate   # 仮想環境に入る
  ```

- [配布用ディレクトリ](dist)からwhlファイルをダウンロードします．

- 以下を実行します．

  ```sh
  $ pip install <ダウンロードしたwhlファイル>
  ```

### サンプルアプリケーションのダウンロード

[配布用ディレクトリ](dist)から`sample_apps.zip`ファイルをダウンロードし，適当なところに展開します．


### オウム返しサンプルアプリケーション

#### 起動

ただオウム返しを行うアプリケーションです．組み込みブロッククラスは使っていません．

```sh
$ dialbb-server sample_apps/parrot/config.yml
```

#### ターミナルからの動作確認

別のターミナルから以下を実行してください．curlをインストールしていない場合は，後述するようにブラウザからテストしてください．


- ```sh
  $ curl -X POST -H "Content-Type: application/json" \
    -d '{"user_id":"user1"}' http://localhost:8080/init
  ```
   以下のレスポンスが帰ります．
  
  ```json
  {"aux_data":null, 
   "session_id":"dialbb_session1", 
   "system_utterance":"I'm a parrot. You can say anything.", 
   "user_id":"user1"}
  ```
  
- 2回目以降のアクセス

  ```sh
  $ curl -X POST -H "Content-Type: application/json" \
    -d '{"user_utterance": "こんにちは", "user_id":"user1", "session_id":"dialbb_session1"}' \
    http://localhost:8080/dialogue
  ```
   以下のレスポンスが帰ります．

  ```json
  {"aux_data":null,
   "final":false,
   "session_id":"dialbb_session1",
   "system_utterance":"You said \"こんにちは\"",
   "user_id":"user1"}
  ```

#### ブラウザからの動作確認

上記でアプリケーションを起動したサーバのホスト名かIPアドレスを`<hostname>`としたとき，ブラウザから以下のURLに接続すると対話画面が現れますので，そこで対話してみてください．

```
http://<hostname>:8080 
```

サーバをWindows 10上で動作させた場合，ブラウザ上に対話画面が出ないことがあります．その場合は，以下のURLに接続すると，簡易な対話画面が出ます．

```
http://<hostname>:8080/test
```

## Simpleアプリケーション

以下の組み込みブロックを用いたサンプルアプリケーションです．`sample_apps/simple_ja/`に日本語版が，`sample_apps/simple_en/`に英語版があります．

- 日本語アプリケーション

  - Japanese Canonicalizer Block
  - LR-CRF Understander  Block  (ロジスティック回帰と条件付き確率場を用いた言語理解)
  - STN Manager  Block (状態遷移ネットワークに基づく対話管理)
- 英語アプリケーション

  - Simple Canonicalizer Block
  - LR-CRF Understander Block
  - STN Manager Block


#### Graphvizのインストール

[Graphvizのサイト](https://graphviz.org/download/)などを参考にGraphvizをインストールします．ただ，Graphvizがなくてもアプリケーションを動作させることは**可能**です．


#### 起動


以下のコマンドで起動します．


- 英語アプリケーション

  ```sh
  $ dialbb-server sample_apps/simple_en/config.yml 
  ```
  
- 日本語アプリケーション

  ```sh
  $ dialbb-server sample_apps/simple_ja/config.yml 
  ```

#### テストセットを用いた動作確認

以下のコマンドで，ユーザ発話を順に処理して対話するテストを行うことができます．

  - 英語

   ```sh
   $ dialbb-test sample_apps/simple_en/config.yml \
     sample_apps/simple_en/test_inputs.txt --output \
     sample_apps/simple_en/_test_outputs.txt
   ```

​    `sample_apps/simple_en/_test_outputs.txt`に対話のやりとりが書き込まれます．

  - 日本語

   ```sh
   $ dialbb-test dialbb/util/test.py sample_apps/simple_ja/config.yml \
     sample_apps/simple_ja/test_inputs.txt --output \
     sample_apps/simple_ja/_test_outputs.txt
   ```

​    `sample_apps/simple_ja/_test_outputs.txt`に対話のやりとりが書き込まれます．

### 実験アプリケーション

`sample_apps/lab_app_ja/` （日本語）`sample_apps/lab_app_en/` （英語）に実験的なアプリケーションがあります（日本語）．組み込みブロックの様々な機能を試すためのアプリケーションです．以下の組み込みブロックを用いています．


- 日本語アプリケーション


    - Japanese Canonicalizer Block 


    - ChatGPT Understander Block


    - ChatGPT NER Block


    - STN Manager Block



- 英語アプリケーション

  - Simple Canonicalizer Block 
  - ChatGPT Understander Block
  - ChatGPT NER Block
  - STN Manager Block

#### 環境変数の設定

  本アプリケーションではOpenAI社のChatGPTを使います．そのため，環境変数`OPENAI_API_KEY`にOpenAIのAPIキーを設定します．以下はbashの例です．

  ```sh
  $ export OPENAI_API_KEY=<OpenAIのAPIキー>
  ```

#### 起動方法

  ```sh
  $ dialbb-server sample_apps/lab_app_ja/config_ja.yml  # 日本語
  $ dialbb-server sample_apps/lab_app_ja/config_en.yml  # 英語
  ```

#### テスト方法

  以下のコマンドで，Simpleアプリケーションでは使用していない機能をテストすることができます．

  ```sh
  $ cd sample_apps/lab_app_ja # 日本語の場合
  $ cd sample_apps/lab_app_en # 英語の場合
  $ dialbb-send-test-requests config.yml test_requests.json
  ```

### ChatGPT対話アプリケーション

以下の組み込みブロックを用い，OpenAIのChatGPTを用いて対話を行います．

- ChatGPT Dialogue Block


#### Pythonライブラリのインストール

  以下を実行します．

  ```sh
  $ pip install -r sample_apps/chatgpt/requirements.txt 
  ```

#### 環境変数の設定

  環境変数OPENAI_API_KEYにOpenAIのAPIキーを設定します．以下はbashの例です．

  ```sh
  $ export OPENAI_API_KEY=<OpenAIのAPIキー>
  ```

#### 起動方法

  日本語版

  ```sh
  $ dialbb-server sample_apps/chatgpt/config_ja.yml 
  ```

  英語版

  ```sh
  $ dialbb-server sample_apps/chatgpt/config_en.yml 
  ```

## 要望・質問・バグ報告

DialBBに関するご要望・ご質問・バグ報告は以下のところに気軽にお寄せください．些細なことや漠然とした質問でも構いません．

  - バグ報告・ドキュメントの不備指摘など: [GitHub Issues](https://github.com/c4a-ri/dialbb/issues)

  - 長期的な開発方針など：[GitHub Discussions](https://github.com/c4a-ri/dialbb/discussions)
  
  - 何でも：`dialbbあっとc4a.jp`


著作権

(c) C4A Research Institute, Inc.
