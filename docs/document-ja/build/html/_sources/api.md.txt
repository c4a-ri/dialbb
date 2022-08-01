# DialBB API ドキュメント

DialBBのアプリケーションはWeb APIとクラスAPIの両方を用いて利用することができます．

## Web API 仕様

### サーバの起動

```sh
$ python run_server.py <config file>
```

### セッションの開始時

- URI

  ```
  http://<server>:8080/init
  ```

- リクエストヘッダ

  ```
  Content-Type: application/json
  ```

- リクエストボディ

  以下の形のjson

      ```json
      {
      "user_id": <ユーザID>,
      "aux_data": <補助データ>
      }
      ```
    
  - `user_id`は必須．`aux_data`は任意．

  - <ユーザID>はユーザに関するユニークなID. 同じユーザが何度も対話する際に，
    以前の対話の内容をアプリが覚えておくために用います．

  - <補助データ>は，クライアントの状態をアプリに送信するために用います．
    フォーマットは任意のJSONオブジェクトで，アプリ毎に決めます．

- レスポンス

    ```json
    {
    "session_id":<セッションID: 文字列>,
    "system_utterance",<システム発話文字列: 文字列>, 
    "user_id":<ユーザID: 文字列>, 
    "final": <対話終了フラグ: ブール値> 
    "aux_data":<補助データ: オブジェクト>
    }
    ```

  - <セッションID>は，対話のセッションのIDです．このURIにPOSTする度に新しいセッションIDが生成されます．
  - <システム発話文字列>は，システムの最初の発話（プロンプト）です．
  - <ユーザID>は，リクエストで送られたユーザのIDです．
  - <対話終了フラグ>は，対話が終了したかどうかを表すブール値です．
  - <補助データ>は，対話アプリがクライアントに送信するデータです．サーバの状態などを送信するのに使います．

### セッション開始後の対話

- URI
  ```
  http://<server>:8080/dialogue
  ```

- リクエストヘッダ

  ```
  Content-Type: application/json
  ```

- リクエストボディ

  以下の形のJSONです．

  ```json
  {"user_id": <ユーザID>,
  "session_id": <セッションID>,
  "user_utterance": <ユーザ発話文字列>,
  "aux_data":<補助データ>}
  ```
  - `user_id`, `session_id`, `user_utterance`は必須．`aux_data`は任意です．
  - <セッションID>は，サーバから送られたセッションIDです．
  - <ユーザ発話文字列>は，ユーザが入力した発話文字列です．

- レスポンス

  セッションの開始時のレスポンスと同じです．

## クラスAPI

### 利用方法

環境変数を以下のように設定します．

```sh
export PYTHONPATH=<DialBBのディレクトリ>:$PYTHONPATH
```

pythonを立ち上げるか，DialBBを呼び出すアプリケーションの中で，以下のようにDialogueProcessorのインスタンスを作成し，processメソッドを呼び出します．

```python
>>> from dialbb.main import DialogueProcessor
>>> dialogue_processor = DialogueProcessor(<configurationファイル>)
>>> response = dialogue_processor.process(<リクエスト>, initial=True) # 対話の開始時
>>> response = dialogue_processor.process(<リクエスト>) # それ以降
```
リクエストとresponse（レスポンス）はJSON形式で，Web APIのリクエスト，レスポンスと同じです．


## デバッグモード＆ロギング

- サーバモードとも起動時の環境変数 `DEBUG`の値が`yes` （大文字小文字は問わない）の時，デバッグモードで動作する．

