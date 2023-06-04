# 実験用アプリケーション

このアプリケーションは組み込みブロックの新機能を試すためのものです．

本ディレクトリで下のコマンドでテストをすることができます．

```sh
$ export DIALBB_HOME=<DialBBのホームディレクトリ>
$ export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
$ python $DIALBB_HOME/dialbb/util/send_test_request.py config.yml test_requests.json
```

`test_requests.json`は，`DialogueProcessor`へのリクエストのリストのリストです．リクエストのリストが一つのセッション分です．リクエストの`user_id`は自動的に付加されます．

このテストの中で，OpenAIのGPTを用いることができます．
その場合，最初に以下を実行してください．

```sh
$ pip install openai
$ export OPENAI_KEY=<OpenAIのAPIキー>
```
