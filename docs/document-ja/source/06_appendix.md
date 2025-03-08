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



## DialBBをpipでインストールせずに利用する方法

GitHubリポジトリからcloneします．cloneしたディレクトリを<DialBBのディレクトリ>とします．

```sh
git clone git@github.com:c4a-ri/dialbb.git <DialBBのディレクトリ>
```

環境変数`PYTHONPATH`を設定します．

```sh
export PYTHONPATH=<DialBBのディレクトリ>:$PYTHONPATH
```

クラスAPIで利用する場合，Pythonを立ち上げた後`dialbb`から必要なモジュールやクラスをimportします．

```python
from dialbb.main import DialogueProcessor
```

WebAPIで利用する場合，コンフィギュレーションファイルを指定してサーバを起動します．

```sh
$ python <DialBBのディレクトリ>/run_server.py [--port <port>] <config file>
```

`port`（ポート番号）のデフォルトは8080です．



## 廃止された機能

### Snips Understander組み込みブロック

SnipsがPython3.9以上ではインストールが困難なため，ver. 0.9で廃止されました．代わりにLR-CRF Understander組み込みブロックを用いてください．

### Whitespace Tokenizer組み込みブロックおよびSudachi Tokenizer組み込みブロック

ver. 0.9で廃止されました．LR-CRF UnderstanderやChatGPT Understanderを使えばTokenizerブロックを使う必要はありません．

### Snips+STNサンプルアプリケーション

ver. 0.9で廃止されました．

