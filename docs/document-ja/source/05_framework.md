(framework)=
# フレームワーク仕様

ここではフレームワークとしてのDialBBの仕様を説明します．Pythonプログラミングの知識がある読者を想定しています．

## 入出力

DialBBのメインモジュールは，クラスAPI（メソッド呼び出し）で，ユーザ発話と付加情報をJSON形式で受けとり，システム発話と付加情報をJSON形式で返します．

メインモジュールは，ブロックを順に呼び出すことによって動作します．各ブロックはJSON形式（pythonの辞書型）のデータを受け取り，JSON形式のデータを返します．

各ブロックのクラスや入出力仕様はアプリケーション毎のコンフィギュレーションファイルで規定します．

### DialogueProcessorクラス

アプリケーションの作成は，`dialbb.main.DialogueProcessor`クラスのオブジェクトを作成することで行います．

これは以下の手順で行います．

- 環境変数PYTHONPATHにDialBBのディレクトリを追加します．

  ```sh
  export PYTHONPATH=<DialBBのディレクトリ>:$PYTHONPATH
  ```

- DialBBを利用するアプリケーションの中で，以下のように`DialogueProcessor`のインスタンスを作成し，`process`メソッド[^fn-process]を呼び出します．
  
  ```python
  from dialbb.main import DialogueProcessor
  dialogue_processor = DialogueProcessor(<コンフィギュレーションファイル> <追加のコンフィギュレーション>)
  response = dialogue_processor.process(<リクエスト>, initial=True)  # 対話セッション開始時
  response = dialogue_processor.process(<リクエスト>) # セッション継続時
  ```
  
  [^fn-process]: processメソッドの仕様はv0.2.0で変更になりました．
  
  
  `<追加のコンフィギュレーション>`は，以下のような辞書形式のデータで，keyは文字列でなければなりません．
  
  ```json
  {
	"<key1>": <value1>,
    "<key2>": <value2>,
    ...
  }
  ```
  これは，コンフィギュレーションファイルから読み込んだデータに追加して用いられます．もし，コンフィギュレーションファイルと追加のコンフィギュレーションで同じkeyが用いられていた場合，追加のコンフィギュレーションの値が用いられます．
  
  `<リクエスト>`と`response`（レスポンス）は辞書型のデータで，以下で説明します．
  
  `DialogueProcessor.process`は**スレッドセーフではありません．**

### リクエスト

#### セッション開始時

以下の形のJSONです．

  ```json
  {
    "user_id": <ユーザID: 文字列>,
    "aux_data": <補助データ: オブジェクト（値の型は任意）>
  }
  ```

  - `user_id`は必須で，`aux_data`は任意です．

  - <ユーザID>はユーザに関するユニークなIDです. 同じユーザが何度も対話する際に，以前の対話の内容をアプリが覚えておくために用います．

  - <補助データ>は，クライアントの状態をアプリに送信するために用います．JSONオブジェクトで，内容はアプリ毎に決めます．

####  セッション開始後

以下の形のJSONです．

  ```json
  {
    "user_id": <ユーザID: 文字列>,
    "session_id": <セッションID: 文字列>,
    "user_utterance": <ユーザ発話文字列: 文字列>,
    "aux_data":<補助データ: オブジェクト (値の型は任意>
  }
  ```

  - `user_id`, `session_id`, `user_utterance`は必須．`aux_data`は任意です．
  - <セッションID>は，サーバのレスポンスに含まれているセッションIDです．
  - <ユーザ発話文字列>は，ユーザが入力した発話文字列です．


### レスポンス

  ```json
  {
    "session_id":<セッションID: 文字列>,
    "system_utterance": <システム発話文字列: 文字列>, 
    "user_id":<ユーザID: 文字列>, 
    "final": <対話終了フラグ: ブール値> 
    "aux_data":<補助データ: オブジェクト（値の型は任意>
  }
  ```

  - <セッションID>は，対話のセッションのIDです．対話開始のリクエストを送信した際に新しいセッションIDが生成されます．
  - <システム発話文字列>は，システムの発話です．
  - <ユーザID>は，リクエストで送られたユーザのIDです．
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
  
  指定されたキーがblackboardにない場合、該当するinputの要素は`None`になります。

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

  入力inputを処理し，出力を返します．入力，出力とメインモジュールのblackboardの関係はコンフィギュレーションで規定されます（「{ref}`configuration`」を参照）．
  `session_id`はメインモジュールから渡される文字列で，対話のセッション毎にユニークなものです．


### 利用できる変数

- `self.config` (辞書型)

   コンフィギュレーションの内容を辞書型データにしたものです．これを参照することで，独自に付け加えた要素を読みこむことが可能です．
   
- `self.block_config` (辞書型)

   ブロックコンフィギュレーションの内容を辞書型データにしたものです．これを参照することで，独自に付け加えた要素を読みこむことが可能です．
   
- `self.name` (文字列)

   コンフィギュレーションに書いてあるブロックの名前です．

- `self.config_dir` (文字列)

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
System: <システム発話>
User: <ユーザ発話>
System: <システム発話>
User: <ユーザ発話>
...
System: <システム発話>
User: <ユーザ発話>
System: <システム発話>
<対話の区切り>
System: <システム発話>
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





