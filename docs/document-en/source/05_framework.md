(framework)=
# Framework Specifications

This section describes the specifications of DialBB as a framework. 

We assume that the reader has some knowledge of Python programming.

## Input and Output

The main module of DialBB has the class API (method invocation), which accepts user speech in JSON format and returns system speech in JSON format.

The main module works by calling blocks in sequence. Each block is formatted in JSON (Python dictionary type) and returns the data in JSON format.

The class and input/output specifications of each block are specified in a configuration file for each application.

各ブロックのクラスや入出力仕様はアプリケーション毎のコンフィギュレーションファイルで規定します．

### DialogueProcessor Class

The application is built by creating an object of class `dialbb.main.DialogueProcessor`

This is done by the following procedure.


- Add the DialBB directory to the `PYTHONPATH` environment variable.

  ```sh
  export PYTHONPATH=<DialBB directory>:$PYTHONPATH
  ```

- In an application that calls DialBB, use the following DialogueProcessor
and calls process method[^fn-process].

  ```python
  >>> from dialbb.main import DialogueProcessor
  >>> dialogue_processor = DialogueProcessor(<コンフィギュレーションファイル> <追加のコンフィギュレーション>)
  >>> response = dialogue_processor.process(<リクエスト>, initial=True)  # 対話セッション開始時
  >>> response = dialogue_processor.process(<リクエスト>) # セッション継続時
  ```
  
  [^fn-process]: processメソッドの仕様はv0.2.0で変更になりました．
  
  
  `<additional configuration>` is data in dictionary form, where keys must be a string, such as
  
  ```json
  {
	"<key1>": <value1>,
    "<key2>": <value2>,
    ...
  }
  ```
  
  This is used in addition to the data read from the configuration file. If the same key is used in the
configuration file and in the additional configuration, the value of the additional configuration is used.
  
   <request> and `response` are dictionary type data, described below.

### Request

#### At the start of the session

JSON in the following form.

  ```json
  {
    "user_id": <user id: string>,
    "aux_data": <auxiliary data: object (each key is a string and the type of its value is arbitrary)>
  }
  ```

  - `user_id` is mandatory and `aux_data` is optional

  - <user id> is a unique ID for a user. This is used for remembering the contents of previous interactions when the same user interacts with the application multiple times.

  - <auxiliary data> is used to send client status to the application. It is an JSON object and its contents are decided on an application-by-application basis.
  
  

####  After the session starts

JSON in the following form.

  ```json
  {"user_id": <user id: string>,
   "session_id": <session id: string>,
   "user_utterance": <user utterance string: string>,
   "aux_data": <auxiliary data: object>}
  ```

  - `user_id`, `session_id`, and `user_utterance` are mandatory, and `aux_data` is optional.
  - <session id> is the session ID included in the responses.
  - <user utterance string> is the utterance made by the user.


### Response

  ```json
  {
    "session_id":<session idD: string>,
    "system_utterance": <system utterance string: string>, 
    "user_id":<user id: string>, 
    "final": <end-of-dialogue flag: bool> 
    "aux_data":<補助データ: データ型は任意>
  }
  ```

  - <セッションID>は，対話のセッションのIDです．このURIにPOSTする度に新しいセッションIDが生成されます．
  - <システム発話文字列>は，システムの最初の発話（プロンプト）です．
  - <use id>は，リクエストで送られたユーザのIDです．
  - <対話終了フラグ>は，対話が終了したかどうかを表すブール値です．
  - <補助データ>は，対話アプリがクライアントに送信するデータです．サーバの状態などを送信するのに使います．


## WebAPI

アプリケーションにWebAPI経由でアクセスすることもできます．

### サーバの起動

環境変数`PYTHONPATH`を設定します．

```sh
export PYTHONPATH=<DialBBのディレクトリ>:$PYTHONPATH
```

コンフィギュレーションファイルを指定してサーバを起動します．

```sh
$ python <DialBBのディレクトリ>/run_server.py [--port <port>] <config file>
```

`port`（ポート番号）のデフォルトは8080です．


### クライアントからの接続（セッションの開始時）

- URI

  ```
  http://<server>:<port>/init
  ```

- リクエストヘッダ

  ```
  Content-Type: application/json
  ```

- リクエストボディ

  クラスAPIの場合のリクエストと同じJSON形式のデータです．

- レスポンス

  クラスAPIの場合のレスポンスと同じJSON形式のデータです．
  
### クライアントからの接続（セッション開始後）


- URI
  ```
  http://<server>:<port>/dialogue
  ```

- リクエストヘッダ

  ```
  Content-Type: application/json
  ```

- リクエストボディ

  クラスAPIの場合のリクエストと同じJSON形式のデータです．

- レスポンス

  クラスAPIの場合のレスポンスと同じJSON形式のデータです．

(configuration)=
## コンフィギュレーション

コンフィギュレーションは辞書形式のデータで，yamlファイルで与えることを前提としています．

コンフィギュレーションに必ず必要なのは`blocks`要素のみです．`blocks`要素は，各ブロックがどのようなものかを規定するもの（これをブロックコンフィギュレーションと呼びます）のリストで，以下のような形をしています．

```
blocks:
  - <ブロックコンフィギュレーション>
  - <ブロックコンフィギュレーション>
  ...
  - <ブロックコンフィギュレーション>
```

各ブロックコンフィギュレーションの必須要素は以下です．

- `name` 

  ブロックの名前．ログで用いられます．

- `block_class`

  ブロックのクラス名です．モジュールを検索するパス（`sys.path`の要素の一つ．環境変数`PYTHONPATH`で設定するパスはこれに含まれます）からの相対で記述します．
  
  コンフィギュレーションファイルのあるディレクトリは，モジュールが検索されるパス（`sys.path`の要素）に自動的に登録されます．
  
  組み込みクラスは，`dialbb.builtin_blocks.<モジュール名>.<クラス名>`の形で指定してください．`dialbb.builtin_blocks`からの相対パスでも書けますが，非推奨です．

- `input`

  メインモジュールからブロックへの入力を規定します．辞書型のデータで，keyがブロック内での参照に用いられ，valueがblackboard（メインモジュールで保持されるデータ）での参照に用いられます．例えば，

  ```yaml
  input: 
    sentence: canonicalized_user_utterance
  ```

  のように指定されていたとすると，ブロック内で`input['sentence']`で参照できるものは，メインモジュールの`blackboard['canonicalized_user_utterance']`です．

- `output`

  ブロックからメインモジュールへの出力を規定します．`input`同様，辞書型のデータで，keyがブロック内での参照に用いられ，valueがblackboardでの参照に用いられます．

  ```yaml
  output:
    output_text: system_utterance
  ```

  の場合，ブロックからの出力を`output`とすると，

  ```python
	blackboard['system_utterance'] = output['output_text']
  ```

  の処理が行われます．`blackboard`がすでに`system_utterance`をキーとして持っていた場合は，その値は上書きされます．

## ブロックの自作方法

開発者は自分でブロックを作成することができます．

ブロックのクラスは`diabb.abstract_block.AbstractBlock`の子孫クラスでないといけません．

### 実装すべきメソッド

- `__init__(self, *args)`
  
   コンストラクタです．以下のように定義します．

   ```
   def __init__(self, *args):
    
        super().__init__(*args)
    
        <このブロック独自の処理>
   ```

- `process(self, input: Dict[str, Any], session_id: str = False) -> Dict[str, Any]`

  入力inputを処理し，出力を返します．入力，出力とメインモジュールのblackboardの関係はコンフィギュレーションで規定されます．（「{ref}`configuration`」を参照）
  `session_id`はメインモジュールから渡される文字列で，対話のセッション毎にユニークなものです．


### 利用できる変数

- `self.config` 

   コンフィギュレーションの内容を辞書型データにしたものです．これを参照することで，独自に付け加えた要素を読みこむことが可能です．
   
- `self.block_config`

   ブロックコンフィギュレーションの内容を辞書型データにしたものです．これを参照することで，独自に付け加えた要素を読みこむことが可能です．
   
- `self.name`

   コンフィギュレーションに書いてあるブロックの名前です．(文字列)

- `self.config_dir`

   コンフィギュレーションファイルのあるディレクトリです．アプリケーションディレクトリと呼ぶこともあります．

### 利用できるメソッド

以下のロギングメソッドが利用できます．

- `log_debug(self, message: str, session_id: str = "unknown")`

  標準エラー出力にdebugレベルのログを出力します．
  `session_id`にセッションIDを指定するとログに含めることができます．

- `log_info(self, message: str, session_id: str = "unknown")`

  標準エラー出力にinfoレベルのログを出力します．
  
- `log_warning(self, message: str, session_id: str = "unknown")`

  標準エラー出力にwarningレベルのログを出力します．

- `log_error(self, message: str, session_id: str = "unknown")`

  標準エラー出力にerrorレベルのログを出力します．


## デバッグモード

Python起動時の環境変数 `DIALBB_DEBUG`の値が`yes` （大文字小文字は問わない）の時，デバッグモードで動作します．この時，`dialbb.main.DEBUG`の値が`True`になります．アプリ開発者が作成するブロックの中でもこの値を参照することができます．

`dialbb.main.DEBUG`が`True`の場合，ロギングレベルはdebugに設定され，その他の場合はinfoに設定されます．

## テストシナリオを用いたテスト

以下のコマンドでテストシナリオを用いたテストができます．

```sh
$ python dialbb/util/test.py <アプリケーションコンフィギュレーション> \
  <テストシナリオ> [--output <出力ファイル>]
```

テストシナリオは以下の形式のテキストファイルです．

```
<対話の区切り>
<System: <システム発話>
User: <ユーザ発話>
System: <システム発話>
User: <ユーザ発話>
...
System: <システム発話>
User: <ユーザ発話>
System: <システム発話>
<対話の区切り>
<System: <システム発話>
User: <ユーザ発話>
System: <システム発話>
User: <ユーザ発話>
...
System: <システム発話>
User: <ユーザ発話>
System: <システム発話>
<対話の区切り>
...

```

<対話の区切り>は，"----init"で始まる文字列です．

テストスクリプトは，<ユーザ発話>を順番にアプリケーションに入力して，システム発話を受け取ります．システム発話がスクリプトのシステム発話と異なる場合はwarningを出します．テストが終了すると，出力されたシステム発話を含め，テストシナリオと同じ形式で対話を出力することができます．テストシナリオと出力ファイルを比較することで，応答の変化を調べることができます．





