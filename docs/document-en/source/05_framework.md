(framework)=
# Framework Specifications

This section describes the specifications of DialBB as a framework. 

We assume that the reader has some knowledge of Python programming.

## Input and Output

The main module of DialBB has the class API (method invocation), which accepts user speech in JSON format and returns system speech in JSON format.

The main module works by calling blocks in sequence. Each block is formatted in JSON (Python dictionary type) and returns the data in JSON format.

The class and input/output specifications of each block are specified in a configuration file for each application.

### The DialogueProcessor Class

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
  >>> dialogue_processor = DialogueProcessor(<configuration file> <additional configuration>)
  >>> response = dialogue_processor.process(<request>, initial=True)  # at the start of a dialogue session
  >>> response = dialogue_processor.process(<request>) # when session continues
  ```
  
  [^fn-process]: The specification of the process method was changed in v0.2.0.
  
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
    "aux_data": <auxiliary data: object (types of values are arbitrary)>}
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
   "aux_data": <auxiliary data: object (types of values are arbitrary)>}
  ```

  - `user_id`, `session_id`, and `user_utterance` are mandatory, and `aux_data` is optional.
  - <session id> is the session ID included in the responses.
  - <user utterance string> is the utterance made by the user.


### Response

  ```json
  {
    "session_id":<session id: string>,
    "system_utterance": <system utterance string: string>, 
    "user_id":<user id: string>, 
    "final": <end-of-dialogue flag: bool> 
    "aux_data": <auxiliary data: object (types of values are arbitrary)>}
  }

  ```
  - <session id> is the ID of the dialog session. Each POST to this URI returns a new session ID is generated.
  - <system utterance string> is the first utterance (prompt) of the system.
  - <user id> is the ID of the user sent in the request.
  - <end-of-dialog flag> is a boolean value indicating whether the dialog has ended or not.
  -<auxiliary data> is data that the application sends to the client. It is used to send
information such as server status. 


## WebAPI

Applications can also be accessed via WebAPI.

### Server startup



環境変数`PYTHONPATH`を設定します．
Set the PYTHONPATH environment variable.


```sh
export PYTHONPATH=<DialBBのディレクトリ>:$PYTHONPATH
```

コンフィギュレーションファイルを指定してサーバを起動します．
Start the server by specifying a configuration file.

```sh
$ python <DialBBのディレクトリ>/run_server.py [--port <port>] <config file>
```

`port`（ポート番号）のデフォルトは8080です．
The default port number is 8080.


### クライアントからの接続（セッションの開始時） Connection from client (at start of session)

- URI

  ```
  http://<server>:<port>/init
  ```

- Request header

  ```
  Content-Type: application/json
  ```

- Request body

  クラスAPIの場合のリクエストと同じJSON形式のデータです．
  The data is in JSON format, the same as the request in the case of the class API.


- Response

  クラスAPIの場合のレスポンスと同じJSON形式のデータです．
  The data is in JSON format, the same as the response in the case of the class API.
  
### Connection from client (after session started)


- URI
  ```
  http://<server>:<port>/dialogue
  ```

- request header

  ```
  Content-Type: application/json
  ```

- request body

  クラスAPIの場合のリクエストと同じJSON形式のデータです．
  The data is in JSON format, the same as the request in the case of the class API.

- response

  クラスAPIの場合のレスポンスと同じJSON形式のデータです．
  The data is in JSON format, the same as the response in the case of the class API.

(configuration)=
## configuration

コンフィギュレーションは辞書形式のデータで，yamlファイルで与えることを前提としています．
The configuration is data in dictionary format and is assumed to be provided in a yaml file.

コンフィギュレーションに必ず必要なのは`blocks`要素のみです．`blocks`要素は，各ブロックがどのようなものかを規定するもの（これをブロックコンフィギュレーションと呼びます）のリストで，以下のような形をしています．
Only the blocks element is required for configuration; the blocks element is a list of what each block
specifies (this is called the block configuration) and has the following form

```
blocks:
  - <Block Configuration>
  - <Block Configuration>
  ...
  - <Block Configuration>
```

各ブロックコンフィギュレーションの必須要素は以下です．

- `name` 

  ブロックの名前．ログで用いられます．
  Name of the block. Used in the log.

- `block_class`

  ブロックのクラス名です．モジュールを検索するパス（`sys.path`の要素の一つ．環境変数`PYTHONPATH`で設定するパスはこれに含まれます）からの相対で記述します．
  
  コンフィギュレーションファイルのあるディレクトリは，モジュールが検索されるパス（`sys.path`の要素）に自動的に登録されます．
  
  組み込みクラスは，`dialbb.builtin_blocks.<モジュール名>.<クラス名>`の形で指定してください．`dialbb.builtin_blocks`からの相対パスでも書けますが，非推奨です．

The class name of the block. The path to search for the module (one of the elements of sys.path, including the path
set in the PYTHONPATH environment variable). The path is relative to the path set in the PYTHONPATH
environment variable.
The directory containing the configuration files is automatically registered in the path (an element of
sys.path) where the module is searched.
Built-in classes should be specified in the form dialbb.built-in_blocks. <class name>.
Relative paths from dialbb.builtin_blocks are also allowed, but are deprecated.

- `input`

  メインモジュールからブロックへの入力を規定します．辞書型のデータで，keyがブロック内での参照に用いられ，valueがblackboard（メインモジュールで保持されるデータ）での参照に用いられます．例えば，

This defines the input from the main module to the block. It is a dictionary type data, where key is used
for references within the block and value is used for references in the blackboard (data stored in the
main module). For example, if


  ```yaml
  input: 
    sentence: canonicalized_user_utterance
  ```

  のように指定されていたとすると，ブロック内で`input['sentence']`で参照できるものは，メインモジュールの`blackboard['canonicalized_user_utterance']`です．

then what can be referenced by input['sentence'] in the block is
blackboard['canonicalized_user_utterance'] i n the main module.

- `output`

  ブロックからメインモジュールへの出力を規定します．`input`同様，辞書型のデータで，keyがブロック内での参照に用いられ，valueがblackboardでの参照に用いられます．

Like input, it is data of dictionary type, where key is used for references within the block and value is
used for references on the blackboard.

  ```yaml
  output:
    output_text: system_utterance
  ```

  の場合，ブロックからの出力を`output`とすると，
  
  
  and if the output from the block is output, then

  ```python
	blackboard['system_utterance'] = output['output_text']
  ```

  の処理が行われます．`blackboard`がすでに`system_utterance`をキーとして持っていた場合は，その値は上書きされます．

If blackboard already has system_utterance as a key, the value is overwritten.

## How to make your own blocks

開発者は自分でブロックを作成することができます．

ブロックのクラスは`diabb.abstract_block.AbstractBlock`の子孫クラスでないといけません．

Developers can create their own blocks.
The block class must be a descendant class of diabb.abstract_block.

### Methods to be implemented

- `__init__(self, *args)`
  
   コンストラクタです．以下のように定義します．
   constructor. It is defined as follows

   ```
   def __init__(self, *args):
    
        super().__init__(*args)
    
        <Process unique to this block>
   ```

- `process(self, input: Dict[str, Any], session_id: str = False) -> Dict[str, Any]`

  入力inputを処理し，出力を返します．入力，出力とメインモジュールのblackboardの関係はコンフィギュレーションで規定されます．（「{ref}`configuration`」を参照）
  `session_id`はメインモジュールから渡される文字列で，対話のセッション毎にユニークなものです．
  
  Processes input and returns output. The relationship between input, output and the main module's
blackboard is defined by the configuration (see Configuration). (See Configuration.) session_id is a
string passed from the main module that is unique for each dialog session.


### Available Variables

- `self.config` 

   コンフィギュレーションの内容を辞書型データにしたものです．これを参照することで，独自に付け加えた要素を読みこむことが可能です．
   
   This is a dictionary type data of the contents of the configuration. By referring to this data, it is possible
to read in elements that have been added by the user.
   
- `self.block_config`

   ブロックコンフィギュレーションの内容を辞書型データにしたものです．これを参照することで，独自に付け加えた要素を読みこむことが可能です．
   
   
   The contents of the block configuration are dictionary type data. By referring to this data, it is possible to
load elements that have been added independently.
   
- `self.name`

   コンフィギュレーションに書いてあるブロックの名前です．(文字列)
   The name of the block as written in the configuration. (string)

- `self.config_dir`

   コンフィギュレーションファイルのあるディレクトリです．アプリケーションディレクトリと呼ぶこともあります．
   
   The directory containing the configuration files. It is sometimes called the application directory.

### Available Methods

以下のロギングメソッドが利用できます．The following logging methods are available

- `log_debug(self, message: str, session_id: str = "unknown")`

  標準エラー出力にdebugレベルのログを出力します．
  `session_id`にセッションIDを指定するとログに含めることができます．
  
  Outputs debug-level logs to standard error output. session_id can be specified a s a session ID to be
included in the log.

- `log_info(self, message: str, session_id: str = "unknown")`

  標準エラー出力にinfoレベルのログを出力します．
  Outputs info level logs to standard error output.
  
- `log_warning(self, message: str, session_id: str = "unknown")`

  標準エラー出力にwarningレベルのログを出力します．
  Outputs warning-level logs to standard error output.

- `log_error(self, message: str, session_id: str = "unknown")`

  標準エラー出力にerrorレベルのログを出力します．
  Outputs error-level logs to standard error output.


## デバッグモード

Python起動時の環境変数 `DIALBB_DEBUG`の値が`yes` （大文字小文字は問わない）の時，デバッグモードで動作します．この時，`dialbb.main.DEBUG`の値が`True`になります．アプリ開発者が作成するブロックの中でもこの値を参照することができます．

When the environment variable DIALBB_DEBUG is set to yes (case-insensitive) during Python startup, the program runs in debug mode. In this case, the value of DIALBB.main.DEBUG is True. This value can also be referenced in blocks created by the application developer.

`dialbb.main.DEBUG`が`True`の場合，ロギングレベルはdebugに設定され，その他の場合はinfoに設定されます．

If dialbb.main.DEBUG is True, the logging level is set to debug; otherwise it is set to info.

## テストシナリオを用いたテスト

以下のコマンドでテストシナリオを用いたテストができます．

The following commands can be used to test with test scenarios.

```sh
$ python dialbb/util/test.py <アプリケーションコンフィギュレーション> \
  <テストシナリオ> [--output <出力ファイル>]
```

テストシナリオは以下の形式のテキストファイルです．

The test scenario is a text file in the following format

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

The <dialog separator> is a string beginning with " init".
The test script receives system speech by inputting <user speech> to the application in turn. If the system
utterances differ from the script's system utterances, a warning is issued. When the test is finished, the dialog
can be output in the same format as the test scenario, including the output system utterances. By comparing
the test scenario with the output file, changes in responses can be examined.



