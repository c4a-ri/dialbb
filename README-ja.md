# [DialBB](https://c4a-ri.github.io/dialbb/index-ja.html): 対話システム構築フレームワーク

ver. 2.0.0 

[English](README.md)
	

## プロジェクトWebサイト

[プロジェクトのメインWebサイト](https://c4a-ri.github.io/dialbb/index-ja.html)に，DialBBの概要，
詳細な仕様を記述したドキュメント，チュートリアルスライド，ノーコードツールのドキュメントなどへのリンクがあります．

## ドキュメント

詳細な仕様やアプリケーションの構築法は[ドキュメント](https://c4a-ri.github.io/dialbb/document-ja/build/html/)を参照して下さい．

本READMEがリリース版ではない場合は，[本READMEと同じバージョンのドキュメント](docs/files/document-ja.zip)をダウンロードしてください．）また，ノーコードツールについては[本READMEと同じバージョンのノーコードツールのドキュメント](docs/no-code/index-ja.md)を参照してください．


## 引用

DialBBを用いた研究に関する論文発表をする際には，以下の論文の引用をお願いします．

- Mikio Nakano and Kazunori Komatani. [DialBB: A Dialogue System Development Framework as an Educational Material](https://aclanthology.org/2024.sigdial-1.56). In Proceedings of the 25th Annual Meeting of the Special Interest Group on Discourse and Dialogue (SIGDIAL-24), pages 664–668, Kyoto, Japan. Association for Computational Linguistics, 2024.

## ライセンス

DialBBはApache License 2.0の下で公開されています．

## サンプルアプリケーションの起動の仕方

### 実行環境

Ubuntu 20.04/Windows 11上のpython 3.13で，以下の手順で動作することを確認しています．すべての組み合わせを完全に確かめたわけではありませんが，Windows 11やMacOS（アップルシリコンを含む）の上で，Python 3.11-3.13を使って動かせなかったという報告は得ていません．

以下の説明はUbuntu上のbashで作業することを仮定しています．他のシェルやWindowsコマンドプロンプトを用いる場合は，適宜読み替えてください．

### DialBBのインストール

- 必要なら仮想環境を構築します．以下はvenvの例です．

  ```sh
  $ python -m venv venv        # 仮想環境をvenvという名前で構築
  $ source venv/bin/activate   # 仮想環境に入る
  ```

- [配布用ディレクトリ](dist)から`dialbb-*-py3-none-any.whl`ファイルをダウンロードします．

- 以下を実行します．

  ```sh
  $ pip install <ダウンロードしたwhlファイル>
  （例： pip install dialbb-2.0.0-py3-none-any.whl)
  ```

### サンプルアプリケーションのダウンロード

サンプルアプリケーションファイルを[docs/files/sample_apps.zip](docs/files/sample_apps.zip)からダウンロードし，適当なところに展開します．

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
   以下のレスポンスが返ります．
  
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
   以下のレスポンスが返ります．

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

サーバをWindows 11上で動作させた場合，ブラウザ上に対話画面が出ないことがあります．その場合は，以下のURLに接続すると，簡易な対話画面が出ます．

```
http://<hostname>:8080/test
```

### LLM対話アプリケーション

LLM（大規模言語モデル）を単一プロンプトテンプレートを用いて対話を行います．

- LLM対話ブロック

#### 環境変数の設定

 本アプリケーションはデフォルトでOpenAIのChatGPTを使います．そのため，環境変数`OPENAI_API_KEY`にOpenAIのAPIキーを設定します．以下はbashの例です．

  ```sh
$ export OPENAI_API_KEY=<OpenAIのAPIキー>
  ```

ワーキングディレクトリの`.env`  に書いても構いません．

```
OPENAI_API_KEY=<OpenAI's API key>
```

コンフィギュレーションファイルを変更して他のLLMを使うこともできます．その場合は，必要なキーを環境変数に設定するか`.env`に書いてください．

#### サーバ起動方法

  日本語版

  ```sh
$ dialbb-server sample_apps/llm_dialogue_ja/config.yml 
  ```

  英語版

  ```sh
$ dialbb-server sample_apps/llm_dialogue_en/config.yml 
  ```

ブラウザから`http://<hostname>:8080` または`http://<hostname>:8080/test`にアクセスしてください。

#### ユーザシミュレーションによるテスト

LLMを用いたユーザシミュレーションによる動作確認も行えます。

 日本語版

```sh
$ dialbb-sim-tester --app_config sample_apps/llm_dialogue_ja/config.yml \
  --test_config sample_apps/llm_dialogue_ja/simulation/config.yml
```

英語版

```sh
$ dialbb-sim-tester --app_config sample_apps/llm_dialogue_en/config.yml \
  --test_config sample_apps/llm_dialogue_en/simulation/config.yml
```

### DST-STNアプリケーション

`sample_apps/dst_stn_ja/` （日本語）`sample_apps/dst_stn_en/` （英語）に以下の組み込みブロックを用いたアプリケーションがあります．様々な機能を試すためのアプリケーションです．以下の組み込みブロックを用いています

- LLMを用いたスロット抽出ブロック
- 状態遷移ネットワークベースの対話管理ブロック

#### 環境変数の設定

 本アプリケーションでもデフォルトでOpenAIのChatGPTを使います．LLM対話アプリケーションと同様にOpenAIのAPIキーを環境変数にセットしてください．

#### Graphvizのインストール

[Graphvizのサイト](https://graphviz.org/download/)などを参考にGraphvizをインストールします．ただ，Graphvizがなくてもアプリケーションを動作させることは**可能**です．

#### 起動方法

  ```sh
  $ dialbb-server sample_apps/dst_stn_ja/config.yml # 日本語アプリ
  $ dialbb-server sample_apps/dst_stn_en/config.yml # 英語アプリ
  ```

ブラウザから`http://<hostname>:8080` または`http://<hostname>:8080/test`にアクセスしてください。

#### ユーザシミュレーションによるテスト

LLMを用いたユーザシミュレーションによる動作確認も行えます。

 日本語版

```sh
$ dialbb-sim-tester --app_config sample_apps/dst_stn_ja/config.yml \
  --test_config sample_apps/dst_stn_ja/simulation/config.yml
```

英語版

```sh
$ dialbb-sim-tester --app_config sample_apps/dst_stn_en/config.yml \
  --test_config sample_apps/dst_stn_en/simulation/config.yml
```

#### 補助データを送信するテスト

  以下のコマンドで，ユーザ発話と共に補助データを送信して様々な機能をテストすることができます．

  ```sh
  $ dialbb-send-test-requests sample_apps/dst_stn_ja/config.yml sample_apps/dst_stn_ja/test_requests.json # 日本語アプリ
  $ dialbb-send-test-requests sample_apps/dst_stn_en/config.yml sample_apps/dst_stn_en/test_requests.json # 英語アプリ
  ```

### RAGアプリケーション

`sample_apps/rag_ja/`（日本語）と`sample_apps/rag_en/`（英語）にRAGアプリケーションがあります．FAQ文書から関連パッセージを検索し，その内容をLLMに渡して応答します．以下の組み込みブロックを用いています．

- パッセージ検索ブロック
- LLM対話ブロック

#### 追加ライブラリのインストール

このアプリケーションを実行するには追加のライブラリのインストールが必要です。以下を実行してください。

```sh
$ pip install <ダウンロードしたdialbb-*.whlファイル>[rag]
（例：pip install dialbb-2.0.0-py3-none-any.whl[rag]）
```

#### 環境変数の設定

本アプリケーションでもデフォルトでOpenAIのChatGPTと埋め込みモデルを使います．LLM対話アプリケーションと同様に，環境変数`OPENAI_API_KEY`にOpenAIのAPIキーをセットするか，`.env`に記述してください．

#### サーバ起動方法

  日本語版

  ```sh
$ dialbb-server sample_apps/rag_ja/config.yml
  ```

  英語版

  ```sh
$ dialbb-server sample_apps/rag_en/config.yml
  ```

起動時にパッセージ検索ブロックが`docs/`配下のファイルを読み込み，必要に応じて`vector_db/`以下にベクトルDBを構築します．ベクトルDBを毎回作り直したい場合は，アプリケーション設定で`clear_before_ingest: True`を有効にしてください．

ブラウザから`http://<hostname>:8080` または`http://<hostname>:8080/test`にアクセスしてください。

#### ユーザシミュレーションによるテスト

LLMを用いたユーザシミュレーションによる動作確認も行えます。

 日本語版

```sh
$ dialbb-sim-tester --app_config sample_apps/rag_ja/config.yml \
  --test_config sample_apps/rag_ja/simulation/config.yml
```

英語版

```sh
$ dialbb-sim-tester --app_config sample_apps/rag_en/config.yml \
  --test_config sample_apps/rag_en/simulation/config.yml
```

### ノーコードツール

以下のコマンドでノーコードツールを起動できます。

```sh
$ dialbb-nc
```

ノーコードツールの使い方は、[docs/no-code/index-ja.md](docs/no-code/index-ja.md)を参照してください。

### DialBBのアンインストール

以下でアンインストールできます．

```sh
$ dialbb-uninstall
$ pip uninstall -y dialbb
```

## 要望・質問・バグ報告

DialBBに関するご要望・ご質問・バグ報告は以下のところに気軽にお寄せください．些細なことや漠然とした質問でも構いません．

  - バグ報告・ドキュメントの不備指摘など: [GitHub Issues](https://github.com/c4a-ri/dialbb/issues)

  - 長期的な開発方針など：[GitHub Discussions](https://github.com/c4a-ri/dialbb/discussions)

  - 何でも：`dialbbあっとc4a.jp`


著作権

(c) C4A Research Institute, Inc.
