# Appendix

## フロントエンド

DialBBには，Web APIにアクセスするための，2種類のサンプルフロントエンドが付属しています．

### シンプルなフロントエンド

以下でアクセスできます．

```
http://<ホスト>:<ポート番号>
```

システム発話とユーザ発話を吹き出しで表示します．

`aux_data`の送信はできません．また，レスポンスに含まれるシステム発話以外の情報は表示されません．

### デバッグ用フロントエンド

以下でアクセスできます．

```
http://<ホスト>:<ポート番号>/test
```

システム発話とユーザ発話をリスト型式で表示します．

`aux_data`の送信ができます．また，レスポンスに含まれる`aux_data`も表示されます．



## DialBBのソースコードを変更する方法

GitHubリポジトリからcloneします．cloneしたディレクトリを<DialBBのディレクトリ>とします．

```sh
git clone git@github.com:c4a-ri/dialbb.git <DialBBのディレクトリ>
```

`uv`で依存関係をインストールします．このとき，DialBB本体も編集可能な形で環境に入るため，ソースコードを変更するとそのまま反映されます．

```sh
cd <DialBBのディレクトリ>
uv sync
```

起動時は`uv run`を付けて実行します．

```sh
uv run dialbb-server [--port <port>] <config file>
```

pythonファイルを指定して起動することもできます（PyCharmやVSCodeなどのIDEを用いる場合はこちらが必要です）．


```sh
uv run python <DialBBのディレクトリ>/run_server.py [--port <port>] <config file>
```


## 廃止された機能

### Snips Understander組み込みブロック

SnipsがPython3.9以上ではインストールが困難なため，ver. 0.9で廃止されました．代わりにLR-CRF Understander組み込みブロックを用いてください．

### Whitespace Tokenizer組み込みブロックおよびSudachi Tokenizer組み込みブロック

ver. 0.9で廃止されました．LR-CRF UnderstanderやChatGPT Understanderを使えばTokenizerブロックを使う必要はありません．

### Snips+STNサンプルアプリケーション

ver. 0.9で廃止されました．

### シンプルアプリケーション

ver. 2.0で廃止されました．

### 実験アプリケーション

ver. 2.0で廃止されました．
