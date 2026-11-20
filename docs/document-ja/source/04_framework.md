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

- DialBBがGitHubのREADMEに従いpipでインストールされているか，`dialbb`がモジュール検索パスにあるとします．

- DialBBを利用するアプリケーションの中で，以下のように`DialogueProcessor`のインスタンスを作成し，`process`メソッドを呼び出します．
  
  ```python
  from dialbb.main import DialogueProcessor
  dialogue_processor = DialogueProcessor(<コンフィギュレーションファイル> <追加のコンフィギュレーション>)
  response = dialogue_processor.process(<リクエスト>, initial=True)  # 対話セッション開始時
  response = dialogue_processor.process(<リクエスト>) # セッション継続時
  ```
  
  
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

  - <セッションID>は，対話のセッションのIDです．対話開始のリクエストを送信した際に新しいセッションIDが生成されます．後述の外部DBを使う場合には，ハッシュ値が使われます．
  - <システム発話文字列>は，システムの発話です．
  - <ユーザID>は，リクエストで送られたユーザのIDです．
  - <対話終了フラグ>は，対話が終了したかどうかを表すブール値です．
  - <補助データ>は，対話アプリがクライアントに送信するデータです．サーバの状態などを送信するのに使います．


## WebAPI

アプリケーションにWebAPI経由でアクセスすることもできます．

### サーバの起動

DialBBがGitHubのREADMEに従いpipでインストールされていることを前提とします．

以下のコマンドで起動します．

```sh
$ dialbb-server [--port <port>] <config file>
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

コンフィギュレーションは辞書形式のデータで，YAMLファイルで与えることを前提としています．

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
  
  指定されたキーがblackboardにない場合，該当するinputの要素は`None`になります．

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

## 対話履歴の保持

(ver 1.2で追加)

### Blackboardへの対話履歴の保持

`blackboard`の`dialogue_history`要素には，メインプロセス内部の処理により，以下の形式の対話履歴が保持されます．

```JSON
[
  {
     "speaker": "user",
     "user_id": <入力のuser_id. user_idが入力にない場合は””>
     "aux_data": <入力のaux_data. aux_dataが入力にない場合は{}>,
     "utterance": ""
  },
  {
    "speaker": "system",
    "aux_data": <出力のaux_data. aux_dataが出力にない場合は{}>,
    "utterance": <システム発話文字列>
  },
  {
     "speaker": "user",
     "user_id": <入力のuser_id. user_idが入力にない場合は””>
     "aux_data": <入力のaux_data. aux_dataが入力にない場合は{}>,
     "utterance": <ユーザ発話文字列>
  }
  ...
]
```

### 発話済み文字列によるシステム発話履歴の更新

セッション継続時のリクエストに `aux_data.spoken_string` を指定すると，履歴の最後のシステム発話の `utterance` を，その文字列で置き換えます．音声の再生が中断された場合などに，ユーザに伝えた部分だけを履歴へ反映できます．クラスAPIでも，`spoken_string` はリクエストの `aux_data` 内に指定します．

```json
{
  "user_id": "user1",
  "session_id": "dialbb_session1",
  "user_utterance": "ちょっと待って",
  "aux_data": {
    "spoken_string": "あいうえ"
  }
}
```

例えば，直前のシステム発話が `あいうえおかきくけこ` の場合，このリクエストを処理すると，履歴内のその発話は `あいうえ` に置き換わります．

- 値は文字列です．空文字列 `""` を指定すると，最後のシステム発話の `utterance` も空文字列になります．未指定または文字列以外の場合，履歴は変更しません．
- `barge_in` の有無にかかわらず適用します．対象となるシステム発話がない場合は何もしません．
- 現在のユーザ発話を履歴に追加する前に置き換えるため，各ブロックには更新後の `dialogue_history` が渡されます．メモリ保持と外部DB保存の両方に適用されます．
- DialBBのメイン処理は，渡された文字列をそのまま使用します．再生位置から部分文字列を求める処理は，マルチモーダル側で行います．

マルチモーダルの標準クライアントは，再生停止時の位置を，次のユーザ音声送信の `send_audio_chunk.playback_position` に付与します．

```json
"playback_position": {
  "utterance_id": 1,
  "completed_units": 2.5,
  "segment_count": 5
}
```

`completed_units` は，再生完了セグメント数に再生中セグメントの経過割合を加えた値です．この例では，全5セグメント中，3つ目の半分まで再生しています．サーバは発話IDとセグメント数を確認し，再生済み部分を計算して，認識したユーザ発話とともに `aux_data.spoken_string` としてDialBBへ送ります．再生位置は，対応するユーザ発話リクエストの作成前に届く必要があります．独自のクライアントは `send_audio_chunk.aux_data.spoken_string` を直接指定することもできます．

部分文字列の長さは，日本語では文字数，英語では空白区切りの単語数を基準に，再生位置の割合を掛けて四捨五入します（小数部分が 0.5 なら切り上げ）．例えば，5文字または5単語の半分まで再生した場合は，先頭の3文字または3単語を残します．各セグメントを等しい重みで扱うため，実際に聞こえた範囲の概算です．

(context_db)=

### 対話履歴の外部DBでの保存

DialBBアプリケーションをWebサーバとして動作させ，リクエストが集中した際にロードバランサを使って複数インスタンスでに処理を分散させる場合，文脈情報を外部DB（MongoDB)に保存することで，一つのセッションを異なるインスタンスで処理することが可能です．

外部DBを使うには，コンフィギュレーションのトップレベルに以下のように`context_db`要素を指定します．

```yaml
context_db:
  host: localhost
  port: 27017
  user: admin
  password: password
```

各キーは以下です．

- `host` （str)

  MongoDBが動作しているホスト名

- `port` (int. デフォルト値`27017`)

  MongoDBのアクセスのためのポート番号

- `user` （str)

  MongoDBのアクセスのためのユーザ名

- `password` （str)

  MongoDBのアクセスのためのパスワード

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

  入力inputを処理し，出力を返します．入力，出力とメインモジュールのblackboardの関係はコンフィギュレーションで規定されます（{numref}`configuration`を参照）．
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

#### ロギング

以下のロギングメソッドが利用できます．

- `log_debug(self, message: str, session_id: str = "unknown")`

  標準エラー出力にdebugレベルのログを出力します．
  `session_id`にセッションIDを指定するとログに含めることができます．

- `log_info(self, message: str, session_id: str = "unknown")`

  標準エラー出力にinfoレベルのログを出力します．
  
- `log_warning(self, message: str, session_id: str = "unknown")`

  標準エラー出力にwarningレベルのログを出力します．

- `log_error(self, message: str, session_id: str = "unknown")`

  標準エラー出力にerrorレベルのログを出力します．後述のデバッグモードの時は，Exceptionを投げます．



## デバッグモード

Python起動時の環境変数 `DIALBB_DEBUG`の値が`yes` （大文字小文字は問わない）の時，デバッグモードで動作します．この時，`dialbb.main.DEBUG`の値が`True`になります．アプリ開発者が作成するブロックの中でもこの値を参照することができます．

`dialbb.main.DEBUG`が`True`の場合，ロギングレベルはdebugに設定され，その他の場合はinfoに設定されます．

## 環境変数の読み込み

上記の`DIALBB_DEBUG`の他にも，商用LLMのAPIキーの設定などに環境変数を用います．環境変数は，bashの場合の`export`などで設定しても良いですが，アプリケーション起動時のカレントディレクトリの`.env`に書くことも可能です．以下のような形式で書きます．

```text
DIALBB_DEBUG=yes
OPENAI_API_KEY=....
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
```

すでに設定されている環境変数は`.env`の記述では上書き**されません．**



## テスト

(test_scenario)=
### テストシナリオを用いたテスト

以下のコマンドでテストシナリオを用いたテストができます．

```sh
$ dialbb-test <アプリケーションコンフィギュレーションファイル> \
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

(test_requests)=

### テストリクエストを用いたテスト

テストシナリオを用いたテストでは`aux_data`を入力できません．`aux_data`を入力するテストを行うには，テストリクエストを用いたテストを行います．

以下のコマンドで実行します．

```bash
$ dialbb-send-test-requests <アプリケーションコンフィギュレーションファイル> ＜テストリクエストファイル＞
```

テストリクエストファイルは以下の形式のJSONファイルです．

```json
[
    [
      <最初のセッションの最初の入力>, 
      <最初のセッションの2番目の入力>, 
      ...
    ],
    [
      <2番目のセッションの最初の入力>, 
      <2番目のセッションの2番目の入力>, 
      ...
    ], 
    ...
]
```

各入力は，以下の形をしています．

- 各セッションの最初の入力（aux_dataがない場合）

  ```json
  { "user_id": <ユーザID>}
  ```

- 各セッションの最初の入力（aux_dataがある場合）

  ```json
  { 
      "user_id": <ユーザID>, 
      "aux_data": <aux_dataの値（辞書）>
  }
  ```

  - 

- 2番目以降の入力（aux_dataがない場合）

  ```json
  {  
      "user_id": <ユーザID>,
      "user_utterance": "<ユーザ発話テキスト>"
  }
  ```

- 2番目以降の入力（aux_dataがある場合）

  ```json
  { 
      "user_id": <ユーザID>,
      "user_utterance": "<ユーザ発話テキスト>",
      "aux_data": <aux_dataの値（辞書）>
  }
  ```

各セッション最初の入力はそのまま，2番目以降は`session_id`が付加されてDialBBアプリケーションに入力されます．

`user_id`は省略しても構いません．その場合，各セッションの最初の入力は，`aux_data`がない場合，空辞書になります．

(sim_tester)=

### ユーザシミュレータを用いたテスト

プロンプトに従って発話を生成するLLM，または別のDialBBアプリケーションをユーザシミュレータとして使うテスタが付属しています．テスト対象アプリケーションはサーバとして起動する必要はなく，テスタから直接呼び出されます．

#### サンプルの動かし方

以下bashの例で説明します．Windows コマンドプロンプトの場合は適宜読み替えてください．

- DialBBをインストールし，サンプルアプリケーションをダウンロードして展開します．

- 環境変数`OPENAI_API_KEY`にOpenAI APIのキーを設定します．

  ```sh
  export OPENAI_API_KEY=<OPENAIのAPIキー>
  ```

- サンプルアプリケーションを展開したディレクトリ（`sample_apps`）で以下のコマンドを実行します．

  ```sh
  dialbb-sim-tester --app_config llm_dialogue_ja/config.yml --test_config llm_dialogue_ja/simulation/config.yml --output _output.txt
  ```

- `_output.txt`に結果が記述されます．

- プログラムの中でテスタを起動するには以下のようにします

  ```python
  from dialbb.sim_tester.main import do_test

  for log in do_test(
      "llm_dialogue_ja/simulation/config.yml",
      "llm_dialogue_ja/config.yml",
      output_file="_output.txt",
  ):
      print(log, end="")
  ```


#### 仕様

- 起動オプション

  ```sh
  dialbb-sim-tester --app_config <DialBBアプリケーションのコンフィギュレーションファイル> --test_config <テストコンフィギュレーションファイル> --output <出力ファイル> [--json_output]
  ```

- `--app_config`と`--test_config`は必須です．`--output`は省略可能です．出力ファイルは通常テキスト形式で，`--json_output`を指定するとJSON形式になります．JSONファイルを保存するには`--output`も指定してください．

#### LLMを直接使うテスト設定

テストコンフィギュレーションは以下のキーをもつYAMLです．

  - `model`: （文字列．任意）モデル指定文字列．デフォルト値は`gpt-5.6-luna`．`provider:model_name` の形式で指定します．例：`google_genai:gemini-2.0-flash-001`．OpenAIのGPTモデルは `openai:` を省略できます．APIキーは利用するプロバイダに対応する環境変数に設定してください．OpenAIの場合は`OPENAI_API_KEY`を使います．旧`OPENAI_KEY`からの自動読み替えは行いません．
  - `language`: （文字列．任意）シミュレータに渡す指示と対話履歴の話者名の言語．`en`（デフォルト値）または`ja`を指定します．日本語のプロンプトを使う場合は`language: ja`を指定してください．
  - `settings`（オブジェクトのリスト．必須）設定のリスト．以下の要素を持つことができる

    - `prompt_template`: （文字列．必須）プロンプトテンプレートを記述したテキストファイルのパス．ファイルパスはコンフィギュレーションファイルからの相対パス．

    - `initial_aux_data`（文字列．任意）対話の最初にDialBBアプリケーションにアクセスする際に，`aux_data`に入れる内容を書いたJSONファイルのパス．パスはコンフィギュレーションファイルからの相対パス．
  - `temperatures`: （浮動小数点数のリスト．任意）LLMの温度パラメータのリスト．デフォルト値は`[0.7]`．`settings`のリストの長さ×このリストの長さのセッションが行われます．GPT-5系モデルでは温度はモデルに渡されません．
  - `max_turns`: (整数．任意）セッションあたりの最大ターン数．デフォルト値15．

各ターンで，プロンプトテンプレートの後に対話履歴がテキストとして追加され，ユーザメッセージとしてLLMに渡されます．システムメッセージにはフレームワーク共通の指示が渡されます．テンプレートに対話履歴用のプレースホルダを記述する必要はありません．`DIALBB_TESTER_DEBUG=yes`を設定すると，生成に使ったプロンプトも表示されます．

```yaml
model: gpt-5.6-luna
language: ja
max_turns: 10
settings:
  - prompt_template: prompt_template1.txt
    initial_aux_data: aux_data1.json
temperatures:
  - 0.7
```

#### DialBBアプリケーションを使うテスト設定

`settings`の代わりに`configs`を指定すると，別のDialBBアプリケーションをユーザシミュレータとして使用します．シミュレータの`system_utterance`がテスト対象へのユーザ発話になり，テスト対象の`system_utterance`がシミュレータへのユーザ発話になります．シミュレータはLLM対話ブロックに限らず，通常のDialBBのブロック構成を使えます．

- `configs`（文字列のリスト．必須）シミュレータのアプリケーション設定ファイルのパス．テスト設定ファイルからの相対パスです．各設定につき1セッションを実行します．
- `max_turns`（整数．任意）セッションあたりの最大ユーザ発話数．デフォルト値は`15`です．テスト対象が`final: true`を返した場合も終了します．
- `start_by_simulator`（真偽値．任意）デフォルト値は`false`で，テスト対象の初期発話から始めます．`true`では，両アプリケーションを初期化した後，シミュレータの初期発話を最初のユーザ発話としてテスト対象に渡します．テスト対象の初期発話は対話ログに含めません．

```yaml
max_turns: 10
start_by_simulator: false
configs:
  - config1.yml
  - config2.yml
```

`configs`と`settings`はどちらか一方を指定してください．`model`，`language`，`temperatures`などのLLM直接利用向けの設定はこの方式では使用しません．モデルやプロンプトは各シミュレータのアプリケーション設定で指定します．

`sample_apps`ディレクトリから実行する例です．このサンプルは`llm_dialogue_ja/simulation_with_dialbb`に含まれます．

```sh
dialbb-sim-tester --app_config llm_dialogue_ja/config.yml --test_config llm_dialogue_ja/simulation_with_dialbb/configs.yml --output _output.json --json_output
```

#### 結果の形式

JSON出力はセッションごとのオブジェクトの配列です．各オブジェクトの`dialogue`には，`speaker`（`system`または`user`）と`utterance`を持つ発話オブジェクトが順に入ります．LLM直接利用の場合は`prompt_template`，`temperature`，`initial_aux_data`も記録します．DialBBアプリケーション利用の場合はシミュレータの設定ファイルのパスを`config`に記録します．

```json
[
  {
    "config": "llm_dialogue_ja/simulation_with_dialbb/config1.yml",
    "dialogue": [
      {"speaker": "system", "utterance": "こんにちは。"},
      {"speaker": "user", "utterance": "こんにちは。少しお話しましょう。"}
    ]
  }
]
```

#### Pythonからの呼び出し

```python
def do_test(
    test_config_file: str,
    app_config_file: str,
    output_file: str | None = None,
    json_output: bool = False,
    prompt_params: dict[str, str] | None = None,
) -> Generator[str, None, None]:
    ...
```

`dialbb.sim_tester.main`からインポートします．`test_config_file`が先，`app_config_file`が後です．`output_file`は保存先，`json_output`は保存形式（`False`ならテキスト）を指定します．`prompt_params`はLLM直接利用のときだけ使用し，テンプレート中の`{key}`を辞書の値で置換します．

戻り値は対話ログの文字列を順次返すジェネレータです．関数を呼ぶだけではテストを実行しません．上の例のように最後まで反復すると，テストが完了し，指定したファイルへの保存も完了します．JSON出力を指定しても，ジェネレータが返す値はログの文字列です．

2.1では旧`test_by_simulation`を`do_test`に変更しました．旧関数をインポートしているプログラムは，関数名と引数，ジェネレータの反復処理を更新してください．
