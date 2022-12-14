# インストールとサンプルアプリケーションの実行の仕方

本章では，DialBBをインストールしてサンプルアプリケーションを実行する方法について説明します．もし以下の作業を行うことが難しければ，詳しい人に聞いてください．

## 実行環境

Ubuntu 20.04およびWindows 10上のpython 3.8.10で，以下の手順で動作することを確認しています．

他のバージョンのPythonでも動作する可能性が高いです．
また，MacOSでも動作しますが，インストールに追加の手順が必要な場合があります．詳細は割愛します．

## DialBBのインストール

githubのソースコードをcloneします．

```sh
$ git clone https://github.com/c4a-ri/dialbb.git
```

## python libraryのインストール

cloneしたディレクトリに移動し，以下を実行してください．

```sh
$ cd dialbb
$ pip install -r requirements.txt 
$ python -m snips_nlu download en（英語アプリケーションを作成・利用する場合）
$ python -m snips_nlu download ja（日本語アプリケーションを作成・利用する場合）
```

- 注意

  - Windows上のAnacondaを用いて実行する場合，Anaconda Promptを管理者モードで起動しないといけない可能性があります．

  - pyenvを使っている場合，以下のエラーが出る可能性があります．

    ```
    ModuleNotFoundError: No module named '_bz2' 
    ```
    
    それに対する対処法は[この記事](https://qiita.com/kasajei/items/5e22161b62f4b84787bc)などを参照ください．


## Graphvizのインストール

[Graphvizのサイト](https://graphviz.org/download/)などを参考にgraphvizをインストールします．
ただ，Graphvizがなくてもアプリケーションを動作させることは可能です．

## オウム返しサンプルアプリケーションのサーバの起動

ただオウム返しを行うアプリケーションです．

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

## 組み込みブロックを用いたサンプルアプリケーションの起動

DialBBには，あらかじめ作成してあるブロック（組み込みブロック）を用いたサンプルアプリケーションがあります．

### 起動

以下のコマンドで起動します


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
http://localhost:8080/test
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

