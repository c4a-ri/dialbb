# DialBB: 対話システム構築フレームワーク

ver.0.8.0

[English](README.md)

## 概要

DialBBは株式会社C4A研究所が開発した対話システムを構築するためのフレームワークです．情報技術の教材として作られました．拡張可能性の高いアーキテクチャを持ち，読みやすいコードで書かれています．ブロックと呼ぶモジュールを組み合わせてシステムを開発できます．開発者は簡単なシステムを組み込みブロックを用いて作ることができ，高度なシステムを自作のブロックを使って作ることもできます．

DialBBのメインモジュールは，メソッド呼び出しまたはWeb API経由で，ユーザ発話の入力をJSON形式で受けとり，システム発話をJSON形式で返します．メインモジュールは，ブロックを順に呼び出すことによって動作します．各ブロックはJSON形式(pythonのdictのデータ)を受け取り，JSON形式のデータを返します．各ブロックのクラスや入出力仕様はアプリケーション毎のコンフィギュレーションファイルで規定します．

![dialbb-arch](docs/images/dialbb-arch.jpg)

## ドキュメント

詳細な仕様やアプリケーションの構築法は[ドキュメント](https://c4a-ri.github.io/dialbb/document-ja/build/html/)を参照して下さい．最新バージョン以外のドキュメントは[リンク集](https://c4a-ri.github.io/dialbb/)にあります．

## チュートリアル

DialBBを簡単に説明した[チュートリアルスライド](docs/tutorial-slides/Introduction-to-DialBB-ja-v0.6.pdf)があります．

## ライセンス

DialBBは非商用向けに公開されています．ライセンスの詳細は[ライセンス](LICENSE)をご覧ください．

## サンプルアプリケーションの起動の仕方

### 実行環境

Ubuntu 20.04/Windows 10上のpython 3.8.10で，以下の手順で動作することを確認しています．すべての組み合わせを完全に確かめたわけではありませんが，Windows 10/11やMacOS（アップルシリコンを含む）の上で，または，Python 3.9+を使って動かせなかったという報告は得ていません．ただ，後述のSnips NLUは基本的にPython 3.9+はサポートしていないため，インストールに工夫が必要かまたは，インストールができない可能性があります．

以下の説明はUbuntu上のbashで作業することを仮定しています．他のシェルやWindowsコマンドプロンプトを用いる場合は，適宜読み替えてください．

### DialBBのインストール

githubのソースコードをcloneします．

```sh
$ git clone https://github.com/c4a-ri/dialbb.git
```

この場合,`dialbb`という名前のディレクトリができます．

特定の名前のディレクトリにインストールしたい場合は以下のようにしてください．

```sh
$ git clone https://github.com/c4a-ri/dialbb.git <ディレクトリ名>

```

できたディレクトリを以下で「DialBBディレクトリ」と呼びます．


### Pythonライブラリのインストール

- <DialBBディレクトリ>に移動します．

- 次に必要なら仮想環境を構築します．以下はvenvの例です．

  ```sh
  $ python -m venv venv  # 仮想環境をvenvという名前で構築
  $ venv/bin/activate   # 仮想環境に入る
  ```

- 次に以下を実行して，最低限のライブラリをインストールします．(ver. 0.6からトップディレクトリの`requirements.txt`には最低限のライブラリのみを書くようにしました．）

  ```python
  $ pip install -r requirements.txt 
  ```

### オウム返しサンプルアプリケーション

#### 起動

ただオウム返しを行うアプリケーションです．組み込みブロッククラスは使っていません．

```sh
$ python run_server.py sample_apps/parrot/config.yml
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

## SNIPS+STNアプリケーション

以下の組み込みブロックを用いたサンプルアプリケーションです．`sample_apps/network_ja/`に日本語版が，`sample_apps/network_en/`に英語があります．

- 日本語アプリケーション

  - Japanese Canonicalizer Block
  - Sudachi Tokenizer  Block ([Sudachi](https://github.com/WorksApplications/SudachiPy)を用いた日本語トークナイザ)
  - SNIPS Understander  Block
  - STN Manager  Block (状態遷移ネットワークに基づく対話管理)
- 英語アプリケーション

  - Simple Canonicalizer Block
  - Whitespace Tokenizer Block
  - SNIPS Understander Block ( [Snips NLU](https://snips-nlu.readthedocs.io/en/latest/)を用いた言語理解)
  - STN Manager Block


### 必要なPythonライブラリのインストール

  本アプリケーションを使用しない場合は，以下の手順はスキップして構いません．

  以下を実行します．

  ```sh
  # 以下のどちらかを実行
  $ pip install -r sample_apps/network_ja/requirements.txt 
  $ pip install -r sample_apps/network_en/requirements.txt 

  # 英語アプリケーションを作成・利用する場合
  $ python -m snips_nlu download en 

  # 日本語アプリケーションを作成・利用する場合
  $ python -m snips_nlu download ja 
  ```

  注意

- 基本的にSnipsはscikit-learnの古いバージョンに依存しているため，Python3.9+では動きません．Python3.9+を使っている場合は，インストール中にエラーが出る可能性があります． その場合，以下のコマンドで解決する可能性があります．

    ```
    pip install Cython==0.29.36 
    pip install --upgrade pip setuptools wheel
    ```

- Windowsでは

    ```
    ModuleNotFoundError: No module named 'setuptools_rust'
    ```

    のようなエラーがでる可能性があります．この時は，まず

    ```sh
    $ pip install --upgrade pip
    ```

     を試してください．それでもうまくいかない場合，以下の方法を試してみてください．

    - https://pypi.org/project/snips-nlu-parsers/#files から `snips_nlu_parsers-0.4.3-cp38-cp38m-win_amd64.whl` をダウンロードし，`snips_nlu_parsers-0.4.3-cp38-cp38-win_amd64.whl` にrenameする．以下でインストールする．

      ```sh
      $ pip install snips_nlu_parsers-0.4.3-cp38-cp38-win_amd64.whl
      ```

    - https://pypi.org/project/snips-nlu-utils/#files から `snips_nlu_utils-0.9.1-cp37-cp37m-win_amd64.whl` をダウンロードし，`snips_nlu_utils-0.9.1-cp38-cp38-win_amd64.whl`にrenameする．以下でインストールする．

      ```sh
      $ pip install snips_nlu_utils-0.9.1-cp38-cp38-win_amd64.whl
      ```

    - 再度以下を実行する．

      ```sh
        $ pip install -r sample_apps/network_ja/requirements.txt 
        $ pip install -r sample_apps/network_en/requirements.txt 
      ```

- Windowsで

  ```
    $ python -m snips_nlu download en 
    $ python -m snips_nlu download ja 
  ```

  を実行したとき，`Creating a shortcut link for 'ja' didn't work`というエラーが出ることがあります．この時はWindowsを開発者モードで実行してください．

- Windows上のAnacondaを用いて実行する場合，Anaconda Promptを管理者モードで起動しないといけない可能性があります．


  - pyenvを使っている場合，以下のエラーが出る可能性があります．

    ```
    ModuleNotFoundError: No module named '_bz2' 
    ```
    
    それに対する対処法は[この記事](https://qiita.com/kasajei/items/5e22161b62f4b84787bc)などを参照ください．

インストールがうまくいかない場合は連絡してください．


#### Graphvizのインストール

[Graphvizのサイト](https://graphviz.org/download/)などを参考にGraphvizをインストールします．ただ，Graphvizがなくてもアプリケーションを動作させることは可能です．


#### 起動


以下のコマンドで起動します．


- 英語アプリケーション

  ```sh
  $ python run_server.py sample_apps/network_en/config.yml 
  ```
  
  アプリケーションディレクトリで起動する場合は以下のようにします．

  ```sh
  $ export DIALBB_HOME=<DialBBのホームディレクトリ>
  $ export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
  $ cd sample_apps/network_en  # アプリケーションディレクトリに移動
  $ python $DIALBB_HOME/run_server.py config.yml 
  ```


- 日本語アプリケーション

  ```sh
  $ python run_server.py sample_apps/network_ja/config.yml 
  ```

  アプリケーションディレクトリで起動する場合は以下のようにします．

  ```sh
  $ export DIALBB_HOME=<DialBBのホームディレクトリ>
  $ export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
  $ cd sample_apps/network_ja  # アプリケーションディレクトリに移動
  $ python $DIALBB_HOME/run_server.py config.yml 
  ```

#### テストセットを用いた動作確認

以下のコマンドで，ユーザ発話を順に処理して対話するテストを行うことができます．

  - 英語

   ```sh
   $ python dialbb/util/test.py sample_apps/network_en/config.yml \
     sample_apps/network_en/test_inputs.txt --output \
     sample_apps/network_en/_test_outputs.txt
   ```

​    `sample_apps/network_en/_test_outputs.txt`に対話のやりとりが書き込まれます．

  - 日本語

   ```sh
   $ python dialbb/util/test.py sample_apps/network_ja/config.yml \
     sample_apps/network_ja/test_inputs.txt --output \
     sample_apps/network_ja/_test_outputs.txt
   ```

​    `sample_apps/network_ja/_test_outputs.txt`に対話のやりとりが書き込まれます．

### 実験アプリケーション

`sample_apps/lab_app_ja/` （日本語）`sample_apps/lab_app_en/` （英語）に実験的なアプリケーションがあります（日本語）．組み込みブロックの様々な機能を試すためのアプリケーションです．以下の組み込みブロックを用いています．


- 日本語アプリケーション


  - Japanese Canonicalizer Block 
  - ChatGPT Understander Block
  - Spacy NER Block (NER using [spaCy](https://spacy.io/)/[GiNZA](https://megagonlabs.github.io/ginza/))
  - STN Manager Block

- 英語アプリケーション

  - Simple Canonicalizer Block 
  - ChatGPT Understander Block
  - Spacy NER Block (NER using [spaCy](https://spacy.io/)/[GiNZA](https://megagonlabs.github.io/ginza/))
  - STN Manager Block

#### Pythonライブラリのインストール

  以下を実行します．

  ```sh
  $ pip install -r sample_apps/lab_app_ja/requirements.txt # 日本語アプリケーション
  $ pip install -r sample_apps/lab_app_en/requirements.txt # 英語アプリケーション
  ```

#### 環境変数の設定

  本アプリケーションではOpenAI社のChatGPTを使います．そのため，環境変数`OPENAI_API_KEY`にOpenAIのAPIキーを設定します．以下はbashの例です．

  ```sh
  $ export OPENAI_API_KEY=<OpenAIのAPIキー>
  ```

#### 起動方法

  ```sh
  $ python run_server.py sample_apps/lab_app_ja/config_ja.yml  # 日本語
  $ python run_server.py sample_apps/lab_app_ja/config_en.yml  # 英語
  ```

  アプリケーションディレクトリで起動する場合は以下のようにします．

  ```sh
  $ export DIALBB_HOME=<DialBBのホームディレクトリ>
  $ export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
  $ cd sample_apps/lab_app_ja  # アプリケーションディレクトリに移動（日本語の場合）
  $ cd sample_apps/lab_app_en  # アプリケーションディレクトリに移動（英語の場合）
  $ python $DIALBB_HOME/run_server.py config.yml 
  ```

#### テスト方法

  以下のコマンドで，Snips+STNアプリケーションでは使用していない機能をテストすることができます．

  ```sh
  $ cd sample_apps/lab_app_ja # 日本語の場合
  $ cd sample_apps/lab_app_en # 英語の場合
  $ export DIALBB_HOME=<DialBBのホームディレクトリ>
  $ export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
  $ python $DIALBB_HOME/dialbb/util/send_test_requests.py config.yml test_requests.json
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
  $ python run_server.py sample_apps/chatgpt/config_ja.yml 
  ```

  英語版

  ```sh
  $ python run_server.py sample_apps/chatgpt/config_en.yml 
  ```

  アプリケーションディレクトリで起動する場合は以下のようにします．

  ```sh
  $ export DIALBB_HOME=<DialBBのホームディレクトリ>
  $ export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
  $ cd sample_apps/chatgpt  # アプリケーションディレクトリに移動
  $ python $DIALBB_HOME/run_server.py config_ja.yml  # 日本語
  $ python $DIALBB_HOME/run_server.py config_en.yml  # 英語
  ```

## 要望・質問・バグ報告

DialBBに関するご要望・ご質問・バグ報告は以下のところに気軽にお寄せください．些細なことや漠然とした質問でも構いません．

  - バグ報告・ドキュメントの不備指摘など: [GitHub Issues](https://github.com/c4a-ri/dialbb/issues)

  - 長期的な開発方針など：[GitHub Discussions](https://github.com/c4a-ri/dialbb/discussions)
  
  - 何でも：`dialbbあっとc4a.jp`


著作権

(c) C4A Research Institute, Inc.
