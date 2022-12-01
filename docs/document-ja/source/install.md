# インストールとサンプルアプリの実行の仕方

本章では，DialBBをインストールしてサンプルアプリケーションを実行する方法について説明します．もし以下の作業を行うことが難しければ，詳しい人に聞いてください．

## 実行環境

Ubuntu 20.04およびWindows 10上のpython 3.8.10, python3.7.9で動作確認を行っていますが，バージョン3.9以上のPythonでも動作すると考えられます．

MacOSの場合、RustとCythonのインストールが別途必要になります。（今後詳述予定）

## DialBBのインストール

githubのソースコードをcloneします．

```sh
$ git clone https://github.com/c4a-ri/dialbb.git
```

## python libraryのインストール

cloneしたディレクトリに移動し，以下を実行してください．

```sh
$ cd dialbb
$ pip install -r requirements.txt （python 3.8の場合）
$ pip install -r requirements3.7.txt （python 3.7の場合）
$ python -m snips_nlu download en
$ python -m snips_nlu download ja
```

- 注意

  - Windows上のAnacondaを用いて実行する場合，Anaconda Promptを管理者モードで起動しないといけない可能性があります．

  - pyenvを使っている場合，以下のエラーが出る可能性があります．
    ```
	ModuleNotFoundError: No module named '_bz2' 
	```
	それに対する対処法は[この記事](https://qiita.com/kasajei/items/5e22161b62f4b84787bc)などを参照ください．


## graphvizのインストール

[Graphvizのサイト](https://graphviz.org/download/)などを参考にgraphvizをインストールします．
ただ，Graphvizがなくてもアプリケーションを動作させることは可能です．

## オウム返しサンプルアプリのサーバの起動

ただオウム返しを行うアプリです．日本語アプリのみです．

```sh
$ python run_server.py sample_apps/parrot/config.yml
```

### 動作確認

別のターミナルから以下を実行してください．

- 最初のアクセス

  ```sh
  $ curl -X POST -H "Content-Type: application/json" \
    -d '{"user_id":"user1"}' http://localhost:8080/init
  ```
   以下のレスポンスが帰ります．

  ```
  {"aux_data":{},
   "session_id":"dialbb_session1",
   "system_utterance":"こちらはオウム返しbotです．何でも言って見てください．",
   "user_id":"user1"}
  ```

- 2回目以降のアクセス

  ```sh
  $ curl -X POST -H "Content-Type: application/json" \
    -d '{"user_utterance": "こんにちは", "user_id":"user1", "session_id":"dialbb_session1"}' \
	http://localhost:8080/dialogue
  ```
   以下のレスポンスが帰ります．

  ```
  {"aux_data":null,
   "session_id":"dialbb_session1",
   "system_utterance":"「こんにちは」と仰いましたね．",
   "user_id":"user1"}
  ```

## 組み込みブロックを用いたサンプルアプリの起動

DialBBには，あらかじめ作成してあるブロック（組み込みブロック）を用いたサンプルアプリがあります．

### 起動

以下のコマンドで起動します


- 英語アプリ

  ```sh
  $ python run_server.py sample_apps/network_en/config.yml 
  ```

- 日本語アプリ

  ```sh
  $ python run_server.py sample_apps/network_ja/config.yml 
  ```

### 動作確認

上記でアプリを起動したサーバのホスト名かIPアドレスを`<hostname>`としたとき，ブラウザから以下のURLに接続すると対話画面が現れますので，そこで対話してみてください．

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
  $ python dialbb/util/test.py sample_apps/network_en/config.yml sample_apps/network_en/test_inputs.txt
  ```

  - 日本語

  ```sh
  $ python dialbb/util/test.py sample_apps/network_ja/config.yml sample_apps/network_ja/test_inputs.txt
  ```

