# [DialBB](https://c4a-ri.github.io/dialbb/index-ja.html): 対話システム構築フレームワーク

ver. 2.0.0

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

Ubuntu 20.04/Windows 11上のpython 3.10.13で，以下の手順で動作することを確認しています．すべての組み合わせを完全に確かめたわけではありませんが，Windows 11やMacOS（アップルシリコンを含む）の上で，Python 3.10-3.13を使って動かせなかったという報告は得ていません．

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
  ```

### サンプルアプリケーションのダウンロード

サンプルアプリケーションファイルを[docs/files/sample_apps.zip](https://c4a-ri.github.io/dialbb/files/sample_apps.zip)からダウンロードし，適当なところに展開します．


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

サーバをWindows 11上で動作させた場合，ブラウザ上に対話画面が出ないことがあります．その場合は，以下のURLに接続すると，簡易な対話画面が出ます．

```
http://<hostname>:8080/test
```

### LLM対話アプリケーション

LLM（大規模言語モデル）を単一プロンプトテンプレートを用いて対話を行います．

- LLM対話ブロック

#### 環境変数の設定

 本アプリケーションはデフォルトでOpenAIのChatGPTを使います。そのため、環境変数OPENAI_API_KEYにOpenAIのAPIキーを設定します．以下はbashの例です．

  ```sh
$ export OPENAI_API_KEY=<OpenAIのAPIキー>
  ```

ワーキングディレクトリの`.env`  に書いても構いません。

```
OPENAI_API_KEY=<OpenAI's API key>
```

コンフィギュレーションファイルを変更して他のLLMを使うこともできます。その場合は、必要なキーを環境変数に設定するか`.env`に書いてください。

#### 起動方法

  日本語版

  ```sh
$ dialbb-server sample_apps/llm_dialogue/config_ja.yml 
  ```

  英語版

  ```sh
$ dialbb-server sample_apps/llm_dialogue/config_en.yml 
  ```


#### Graphvizのインストール

[Graphvizのサイト](https://graphviz.org/download/)などを参考にGraphvizをインストールします．ただ，Graphvizがなくてもアプリケーションを動作させることは**可能**です．

### 実験アプリケーション

`sample_apps/dst_st_ja/` （日本語）`sample_apps/dst_st_en/` （英語）に実験的なアプリケーションがあります（日本語）．組み込みブロックの様々な機能を試すためのアプリケーションです．以下の組み込みブロックを用いています．


- LLMを用いたスロット抽出ブロック
- 状態遷移ネットワークベースの対話管理ブロック

#### 環境変数の設定

 本アプリケーションでもデフォルトでOpenAIのChatGPTを使います。LLM対話アプリケーションと同様にOpenAIのAPIキーを環境変数にセットしてください。

#### 起動方法

  ```sh
  $ dialbb-server sample_apps/dst_stn_ja/config.yml # 日本語アプリ
  $ dialbb-server sample_apps/dst_stn_en/config.yml # 英語アプリ
  ```

#### テスト方法

  以下のコマンドで，様々な機能をテストすることができます．

  ```sh
  $ dialbb-send-test-requests sample_apps/dst_stn_ja/config.yml test_requests.json # 日本語アプリ
  $ dialbb-send-test-requests sample_apps/dst_stn_ja/config.yml test_requests.json # 英語アプリ
  ```

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
