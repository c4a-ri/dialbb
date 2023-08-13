# インストールとサンプルアプリケーションの実行の仕方

本章では，DialBBをインストールしてサンプルアプリケーションを実行する方法について説明します．もし以下の作業を行うことが難しければ，詳しい人に聞いてください．

## 実行環境

Ubuntu 20.04上のpython 3.8.10および3.9.12で，以下の手順で動作することを確認しています．

以下の説明はUbuntu上のbashで作業することを仮定しています．他のシェルやWindowsコマンドプロンプトを用いる場合は，適宜読み替えてください．

## DialBBのインストール

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


## Pythonライブラリのインストール

- <DialBBディレクトリ>に移動します．

- 次に必要なら仮想環境を構築します．以下はvenvの例です．

  ```sh
  $ python -m venv venv  # 仮想環境をvenvという名前で構築
  $ venv/bin/activate   # 仮想環境に入る
  ```

- 次に以下を実行して，最低限のライブラリをインストールします．

  ```python
  $ pip install -r requirements.txt 
  ```

## オウム返しサンプルアプリケーション

### 起動

ただオウム返しを行うアプリケーションです．組み込みブロッククラスは使っていません．

```sh
$ python run_server.py sample_apps/parrot/config.yml
```


### 動作確認

別のターミナルから以下を実行してください．
curlをインストールしていない場合は，「{ref}`test_with_browser`」に書いてある方法でテストしてくださ
い．


- 最初のアクセス

  ```sh
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

(snips_network_app)=
## SNIPS+ネットワークベース対話管理アプリケーション

以下の組み込みブロックを用いたサンプルアプリケーションです．
`sample_apps/network_ja/`に日本語版が，`sample_apps/network_en/`に英語があります．

- 日本語アプリケーション

  - {ref}`japanese_canonicalizer`
  - {ref}`sudachi_tokenizer`
  - {ref}`snips_understander`
  - {ref}`stn_manager`

- 英語アプリケーション

  - {ref}`simple_canonicalizer`
  - {ref}`whitespace_tokenizer`
  - {ref}`snips_understander`
  - {ref}`stn_manager`


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

 - 途中でエラーになり，Rustなどの追加のソフトウェアのインストールを求められる場合があります．その場合，指示にしがってインストールしてください．うまくいかない場合はREADMEに書いてある連絡先に連絡してください．

  - python3.9以上の場合，
  
    ```
	ModuleNotFoundError: No module named 'setuptools_rust'
    ```
	などのエラーが出るかもしれません．その場合，以下のコマンドで解決する可能性があります．
	
	```
	pip install --upgrade pip setuptools wheel
    ```

     その他，エラーメッセージに応じて必要なライブラリをインストールしてください．不明点があったりうまくいかなったりした場合は連絡してください．
	 


  - Windows上のAnacondaを用いて実行する場合，Anaconda Promptを管理者モードで起動しないといけない可能性があります．

  - pyenvを使っている場合，以下のエラーが出る可能性があります．

    ```
    ModuleNotFoundError: No module named '_bz2' 
    ```
    
    それに対する対処法は[この記事](https://qiita.com/kasajei/items/5e22161b62f4b84787bc)などを参照ください．


### Graphvizのインストール

[Graphvizのサイト](https://graphviz.org/download/)などを参考にGraphvizをインストールします．
ただ，Graphvizがなくてもアプリケーションを動作させることは可能です．


### 起動


以下のコマンドで起動します．


- 英語アプリケーション

  ```sh
  $ python run_server.py sample_apps/network_en/config.yml 
  ```

- 日本語アプリケーション

  ```sh
  $ python run_server.py sample_apps/network_ja/config.yml 
  ```

(test_with_browser)=
### 動作確認

上記でアプリケーションを起動したサーバのホスト名かIPアドレスを`<hostname>`としたとき，ブラウザから以下のURLに接続すると対話画面が現れますので，そこで対話してみてください．

```
http://<hostname>:8080 
```

サーバをWindows上で動作させた場合，ブラウザ上に対話画面が出ないことがあります．その場合は，以下のURLに接続すると，簡易な対話画面が出ます．

```
http://<hostname>:8080/test
```

### テストセットを用いた動作確認

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

## 実験アプリケーション

`sample_apps/lab_app_ja/`に実験的なアプリケーションがあります（日本語のみ）．組み込みブロックの様々な機能を試すためのアプリケーションです．以下の組み込みブロックを用いています．


- {ref}`japanese_canonicalizer`
- {ref}`sudachi_tokenizer`
- {ref}`snips_understander`
- {ref}`spacy_ner`
- {ref}`stn_manager`

### Pythonライブラリのインストール

  以下を実行します．

  ```sh
  $ pip install -r sample_apps/lab_app_ja/requirements.txt 
  ```

### 環境変数の設定

本アプリケーションではOpenAIのChatGPTを使うことができます．ChatGPTを使うためには，環境変数`OPENAI_KEY`にOpenAIのAPIキーを設定します．以下はbashの例です．

```sh
$ export OPENAI_KEY=<OpenAIのAPIキー>
```

環境変数`OPENAI_KEY`が指定されていない場合，ChatGPTを使わずに動作します．
  
### 起動方法

  ```sh
  $ python run_server.py sample_apps/lab_app_ja/config_ja.yml 
  ```

### テスト方法

以下のコマンドで、{ref}`snips_network_app`では使用していない機能をテストすることができます。

  ```sh
  $ cd sample_apps/lab_app_ja
  $ export DIALBB_HOME=<DialBBのホームディレクトリ>
  $ export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
  $ python $DIALBB_HOME/dialbb/util/send_test_request.py config.yml test_requests.json
  ```

## ChatGPTを用いたアプリケーション

以下の組み込みブロックを用い，OpenAIのChatGPTを用いて対話を行います．

- {ref}`chatgpt_dialogue`


### Pythonライブラリのインストール

  以下を実行します．

  ```sh
  $ pip install -r sample_apps/chatgpt/requirements.txt 
  ```

### 環境変数の設定

環境変数OPENAI_KEYにOpenAIのAPIキーを設定します．以下はbashの例です．

```sh
$ export OPENAI_KEY=<OpenAIのAPIキー>
```
  
### 起動方法

  日本語版

  ```sh
  $ python run_server.py sample_apps/chatgpt/config_ja.yml 
  ```

  英語版

  ```sh
  $ python run_server.py sample_apps/chatgpt/config_en.yml 
  ```



