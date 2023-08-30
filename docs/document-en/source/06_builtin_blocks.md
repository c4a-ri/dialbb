<<<<<<< HEAD
(builtin-blocks)=
# Specification of built-in block class

Built-in block classes are block classes that are included in DialBB in advance.

In ver 0.3, the canonicalization block class has been changed. In addition, a new block class for word segmentation has been introduced. The input to the SNIPS language understanding block has been changed accordingly.

Below, the explanation of the blocks that deal with only Japanese is omitted.

## Simple canonicalizer (simple string canonicalizer block)

(`dialbb.builtin_blocks.preprocess.simple_canonicalizer.SimpleCanonicalizer`)

Canonicalizes user input sentences. The main target language is English.

### Input/Output

- input
  - `input_text`: Input string (string)
    - Example: "I  like ramen".

- output (e.g. of dynamo)
  - `output_text`: string after normalization (string)
    - Example: "i like ramen".

### Description of process

Performs the following processing on the input string.

- Deletes leading and tailing spaces
- Replaces upper-case alphabetic characters by lower-case characters
- Deletes line breaks
- Converts a sequence of spaces into a single space

## Whitespace tokenizer (whitespace-based word segmentation block)

(`dialbb.builtin_blocks.tokenization.whitespace_tokenizer.WhitespaceTokenizer`)

Splits input into words separated by spaces. This is mainly for English.

### Input/Output

- input
  - `input_text`: Input string (string)
    - Example: "i like ramen".

- output (e.g. of dynamo)
  - `tokens`: list of tokens (list of strings)
    - Example: ['i','like','ramen'].
  - `tokens_with_indices`: List of token information (list of objects of class `dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`). Each token information includes the indices of start and end points in the input string.

### Description of process

Splits the input string canonicalized by the simple canonicalizer by whitespace.

## SNIPS understander (language understanding block using SNIPS)

(`dialbb.builtin_blocks.understanding_with_snips.snips_understander.Understander`)  

Determines the user utterance type (also called intent) and extracts the slots using [SNIPS_NLU](https://snips-nlu.readthedocs.io/en/latest/).

Performs language understanding in Japanese if the `language` element of the configuration is `ja`, and language understanding in English if it is `en`. 

At startup, this block reads the knowledge for language understanding written in Excel, converts it into SNIPS training data, and builds the SNIPS model.

At runtime, it uses the SNIPS model for language understanding.


### Input/Output

- input
  - `tokens`: list of tokens (list of strings)
    - Examples: ['I' 'like', 'chicken', 'salad' 'sandwiches'].
  

- output 

  - `nlu_result`: language understanding result (dict or list of dict)
    
	  - If the parameter `num_candidates` of the 	block configuration described below is 1, the language understanding result is a dictionary type in the following format.
	
	    ```json
	     {"type": <user utterance type (intent)>,. 
	      "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}
	    ```

	    The following is an example.	  

	    ```json
	     {"type": "tell-like-specific-sandwich", "slots": {"favorite-sandwich": "roast beef sandwich"}}
	    ```

	  - If `num_candidates` is greater than or equal to 2, it is a list of multiple candidate comprehension results.
	  
	    ```json
	     [{"type": <user utterance type (intent)>, 
	       "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}, ...
	      {"type": <user utterance type (intent)>,. 
	       "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}, ...
	      ....]
	    ```

### Block configuration parameters

- `knowledge_file` (string)

   Specifies the Excel file that describes the knowledge. The file path must be relative to the directory where the configuration file is located.

- `function_definitions`(string)


   Specifies the name of the module that defines the dictionary functions (see {ref}`dictionary_function`). If there are multiple modules, connect them with `':'`. The module must be in the module search path. (The directory of the configuration file is in the module search path.)

- `flags_to_use`(list of strings)

   Specifies the flags to be used. If one of these values is written in the `flag` column of each sheet, it is read. If this parameter is not set, all rows are read.

- `canonicalizer` 

   Specifies the canonicalization information to be performed when converting language comprehension knowledge to SNIPS training data.

   - `class`
   
      Specifies the class of the normalization block. Basically, the same normalization block used in the application is specified.


- `tokenizer` 

   Specifies the tokenization information to be used when converting language understanding knowledge to SNIPS training data.

   - `class`
   
      Specifies the class of the tokenization block. Basically, the same tokenization block used in the application is specified.

	  
- `num_candidates` (Integer. Default value `1`)

   Specifies the maximum number of language understanding results (n for n-best).

- `knowledge_google_sheet` (hash)

  - Excelの代わりにGoogle Sheetを用いる場合の情報を記述します．（Google Sheetを利用する際の設定は[こはたさんの記事](https://note.com/kohaku935/n/nc13bcd11632d)が参考になりますが，Google Cloud Platformの設定画面のUIがこの記事とは多少変わっています．）

  - This includes information for using Google Sheet instead of Excel.
  
    - `sheet_id` (string)

      Google Sheet ID.

    - `key_file`(string)
 
       Specify the key file to access the Goole Sheet API as a relative path from the configuration file directory.

(nlu_knowledge)=

### Language Understanding Knowledge

Language understanding knowledge consists of the following four sheets.

| sheet name | contents |
| ---------- | -------------------------------------- |
| utterances | examples of utterances by type |
| slots | relationship between slots and entities |
| entities | Information about entities |
| dictionary | dictionary entries and synonyms per entity |

The sheet name can be changed in the block configuration, but since it is unlikely to be changed, a detailed explanation is omitted.

#### utterances sheet

Each row consists of the following columns

- `flag`      

   Flags to be used or not. Y: yes, T: test, etc. are often written. Which flag's rows to use is specified in the configuration. In the configuration of the sample application, all rows are used.


- `type`     

   User utterance type (Intent)        

- `utterance` 

   発話例．スロットを`(豚骨ラーメン)[favorite_ramen]が好きです`のように`(<スロットに対応する言語表現>)[<スロット名>]`で表現します．スロットに対応する言語表現＝言語理解結果に表れる（すなわちmanagerに送られる）スロット値ではないことに注意．言語表現が`dictionary`シートの`synonyms`カラムにあるものの場合，スロット値は，`dictionary`シートの`entity`カラムに書かれたものになります． 

   Example of speech. A slot is represented by `(<language expression corresponding to the slot>)[<slot name>]`, as in `(I like (pork bone ramen)[favorite_ramen]. Note that the language expression corresponding to a slot does not = the slot value that appears in the language comprehension result (i.e., is sent to manager). If the language expression is from the `synonyms` column of the `dictionary` sheet, the slot value will be from the `entity` column of the `dictionary` sheet.


The sheets that this block uses, including the utterance sheets, can have other columns than these.

#### slots sheet

Each row consists of the following columns.

- `flag`

  Same as on the utterance sheet.

- `slot name` 

  スロット名．utterancesシートの発話例で使うもの．言語理解結果でも用います．
  Slot name, used in the speech examples in the utterances sheet. Also used in the language comprehension results.

- `entity class`

  エンティティクラス名．スロットの値がどのようなタイプの名詞句なのかを表します．異なるスロットが同じエンティティクラスを持つ場合があります．例えば，`(東京)[source_station]から(京都)[destination_station]までの特急券を買いたい`のように，`source_station, destination_station`とも`station`クラスのエンティティを取ります．
  `entity class`カラムの値として辞書関数（`dialbb/<関数名>`の形）を使うことができます．これにより，dictionaryシートに辞書情報を記述する代わりに，関数呼び出しで辞書記述を得ることができます．（例: `dialbb/location`）関数は以下の「{ref}`dictionary_function`」で説明します．
  またentity classカラムの値は，SNIPSの[builtin entity](https://snips-nlu.readthedocs.io/en/latest/builtin_entities.html)でも構いません．（例: `snips/city`）
  Entity class name. This indicates what type of noun phrase the slot value is. Different slots may have the same entity class. For example, `I want to buy an express ticket from (Tokyo)[source_station] to (Kyoto)[destination_station]`, both `source_station, destination_station` have entity of class `station`. Both `source_station and `destination_station` are entities of the `station` class.
  You can use a dictionary function (of the form `dialbb/<function name>`) as the value of the   `entity class` column. This allows you to obtain a dictionary description with a function call instead of writing the dictionary information on a dictionary sheet (e.g. `dialbb/location`). （The function (e.g. `dialbb/location`) is described in "{ref}`dictionary_function`" below.
  The value of the entity class column can also be a SNIPS [builtin entity](https://snips-nlu.readthedocs.io/en/latest/builtin_entities.html). (e.g. `snips/city`)


  SNIPSのbuiltin entityを用いる場合，以下のようにしてインストールする必要があります．
  If you use the   SNIPS builtin entity, you must install it as follows

```sh
	$ snips-nlu download-entity snips/city en
```

​	SNIPSのbuiltin entityを用いた場合の精度などの検証は不十分です．
    Accuracy and other aspects of the 	SNIPS builtin entity have not been fully verified.

#### entities sheet

Each row consists of the following columns

- `flag`

   Same as on the utterance sheet.

- `entity class`

  エンティティクラス名．slotsシートで辞書関数を指定した場合は，こでも同じように辞書関数名を書く必要があります．
   Entity class name. If a dictionary function is specified on the slots sheet, the same dictionary function name must be written here.


- `use synonyms`

  [同義語を使うかどうか](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#entity-values-synonyms) (`Yes`または`No`)
  [Synonyms or not](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#entity-values-synonyms) (`Yes` or `No`)

- `automatically extensible`

  [辞書にない値でも認識するかどうか](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#auto-extensible) (`Yes`または`No`)
  [Whether values not in dictionary are recognized or not](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#auto-extensible) (`Yes` or `No`)


- `matching strictness`

  [エンティティのマッチングの厳格さ](https://snips-nlu.readthedocs.io/en/latest/api.html) `0.0` - `1.0`
  [Strictness of matching entities](https://snips-nlu.readthedocs.io/en/latest/api.html) `0.0` - `1.0`.


#### dictionary sheet

Each row consists of the following columns

- `flag`

  utterancesシートと同じ
  Same as on the TUTTERANCE sheet

- `entity class`

   entity class name

- `entity`

   辞書エントリー名．言語理解結果にも含まれます．
   The name of the dictionary entry. Also included in the language understanding result.

- `synonyms`

   同義語を`,`または `，`または`，`で連結したもの
   Synonyms joined by `,` or `, ` or `, `

(dictionary_function)=
#### 開発者による辞書関数の定義
#### Dictionary function definitions by developers
辞書関数は，主に外部のデータベースなどから辞書情報を取ってくるときに利用します．

辞書関数はブロックコンフィギュレーションの`dictionary_function`で指定するモジュールの中で定義します．

辞書関数は引数にコンフィギュレーションとブロックコンフィギュレーションを取ります．これらに外部データベースへの接続情報などが書いてあることを想定しています．

辞書関数の返り値は辞書型のリストで，`{"value": <文字列>, "synonyms": <文字列のリスト>}`の形の辞書型のリストです．`"synonyms"`キーはなくても構いません．

以下に辞書関数の例を示します．

Dictionary functions are mainly used to retrieve dictionary information from external databases.

Dictionary functions are defined in the module specified by `dictionary_function` in the block configuration.

The dictionary function takes configuration and block configuration as arguments. It is assumed that the configuration and block configurations contain connection information to external databases.

The return value of the dictionary function is a list of dictionary types of the form `{"value": <string>, "synonyms": <list of strings>}`. The ``synonyms"`` key is optional.

Examples of dictionary functions are shown below.


```python
def location(config: Dict[str, Any], block_config: Dict[str, Any]) \
    -> List[Dict[str, Union[str, List[str]]]]:
    return [{"value": "札幌", "synonyms": ["さっぽろ", "サッポロ"]},
            {"value": "荻窪", "synonyms": ["おぎくぼ"]},
            {"value": "徳島"}]
```

````python
def location(config: Dict[str, Any], block_config: Dict[str, Any]) \
    -> List[Dict[str, Union[str, List[str]]]]:.
    return [{"value": "Sapporo", "synonyms": ["Sapporo", "Sapporo"]}, }
            {"value": "Ogikubo", "synonyms": ["ogikubo"]},.
            {"value": "Tokushima"}]
````


#### SNIPSの訓練データ
#### SNIPS training data

アプリを立ち上げると上記の知識はSNIPSの訓練データに変換され，モデルが作られます．

SNIPSの訓練データはアプリのディレクトリの`_training_data.json`です．このファイルを見ることで，うまく変換されているかどうかを確認できます．

When the application is launched, the above knowledge is converted into SNIPS training data and a model is created.

The SNIPS training data is `_training_data.json` in the application directory. By looking at this file, you can check if the conversion is successful.


(stn_manager)=
## STN manager （状態遷移ネットワークベースの対話管理ブロック）
## STN manager (state transition network-based dialogue management block)

(`dialbb.builtin_blocks.stn_manager.stn_management`)  

状態遷移ネットワーク(State-Transition Network)を用いて対話管理を行います．
Dialogue management is performed using a State-Transition Network.

- 入力
  - `sentence`: 正規化後のユーザ発話（文字列）
  - `nlu_result`:言語理解結果（辞書型または辞書型のリスト）
  - `user_id`: ユーザID（文字列）
  - `aux_data`: 補助データ（辞書型）（必須ではありませんが指定することが推奨されます）
- 出力
  - `output_text`: システム発話（文字列）
     例：
	  ```
	  "醤油ラーメン好きなんですね"
	  ```
  - `final`: 対話終了かどうかのフラグ（ブール値）
  - `aux_data`: 補助データ（辞書型）(ver. 0.4.0で変更）
     入力の補助データを，後述のアクション関数の中でアップデートしたものに，遷移した状態のIDを含めたもの．アクション関数の中でのアップデートは必ずしも行われるわけではない．遷移した状態は，以下の形式で付加される．
     ```json
	 {"state": "特定のラーメンが好き"}
     ```
     
- input
  - `sentence`: User utterance after normalization (string)
  - `nlu_result`: language understanding result (dictionary type or list of dictionary types)
  - `user_id`: User ID (string)
  - `aux_data`: auxiliary data (dictionary type) (not required, but recommended)
- output (e.g. of dynamo)
  - `output_text`: System speech (string)
     Example:
	  ````
	  "So you like soy sauce ramen."
	  ````
  - `final`: boolean flag indicating whether the dialog is finished or not.
  - `aux_data`: auxiliary data (dictionary type) (changed in ver. 0.4.0)
     The auxiliary data of the input is updated in the action function described below, including the ID of the transitioned state. Updates are not necessarily performed in the action function. The transitioned state is added in the following format.
     ```json
	 {"state": "I like a particular ramen" }
     ````
     
### ブロックコンフィギュレーションのパラメータ
### Block configuration parameters

- `knowledge_file`（文字列）

  シナリオを記述したExcelファイルを指定します．コンフィギュレーションファイルのあるディレクトリからの相対パスで記述します．
  Specifies an Excel file describing the scenario. The file must be relative to the configuration file directory.

- `function_definitions` (string)

  シナリオ関数（{ref}`dictionary_function`を参照）を定義したモジュールの名前です．複数ある場合は`':'`でつなぎます．モジュール検索パスにある必要があります．（コンフィギュレーションファイルのあるディレクトリはモジュール検索パスに入っています．）
  The name of the module that defines the   scenario function (see {ref}`dictionary_function`). If there are multiple modules, connect them with `':'`. The module must be in the module search path. (The directory containing the configuration files is in the module search path.)


- `flags_to_use` (list of strings)

  各シートの`flag`カラムにこの値のうちのどれかが書かれていた場合に読み込みます．
  If one of these values is written in the `flag` column of each sheet, it is read.

- `knowledge_google_sheet` (ハッシュ)

  SNIPS Understanderと同じです．
  Same as SNIPS Understander.

- `scenario_graph`: (ブール値．デフォルト値`False`）

   この値が`True`の場合，シナリオシートの`system utterance`カラムと`user utterance example`カラムの値を使って，グラフを作成します．これにより，シナリオ作成者が直感的に状態遷移ネットワークを確認できます．
   If this value is `True`, the values in the `system utterance` and `user utterance example` columns of the scenario sheet are used to create the graph. This allows the scenario creator to intuitively see the state transition network.

   
- `repeat_when_no_available_transitions` (Boolean. Default value is `False`)

   この値が`True`のとき，デフォルト遷移（後述）以外の遷移で条件に合う遷移がないとき，遷移せず同じ発話を繰り返します．
   When this value is `True`, if there is no transition other than the default transition (see below) that matches the condition, the same utterance is repeated without transition.

(scenario)=
### Dialogue Management Knowledge Description

対話管理知識（シナリオ）は，Excelファイルのscenarioシートです．
The dialog management knowledge (scenario) is a scenario sheet in an Excel file.

このシートの各行が，一つの遷移を表します．各行は次のカラムからなります．
Each row of the sheet represents a transition. Each row consists of the following columns

- `flag`

  utteranceシートと同じ
  Same as on the TURTARANCE sheet.

- `state`

  遷移元の状態名
  Transition source state name

- `system utterance`

  `state`の状態で生成されるシステム発話の候補．システム発話文字列に含まれる{<変数>}は，対話中にその変数に代入された値で置き換えられます．`state`が同じ行は複数あり得ますが，同じ`state`の行の`system utterance`すべてが発話の候補となり，ランダムに生成されます．
    Candidate system utterances generated in the `state` state. The {<variable>} in the system utterance string is replaced by the value assigned to the variable during the dialogue. There can be multiple lines with the same `state`, but all `system utterance` candidates for the same `state` line are generated randomly.


- `user utterance example`

  ユーザ発話の例．対話の流れを理解するために書くだけで，システムでは用いられません．
  Example of user speech. It is only written to understand the flow of the dialogue, and is not used by the system.


- `user utterance type`

  ユーザ発話を言語理解した結果得られるユーザ発話のタイプ．遷移の条件となります．
  The type of user utterance resulting from linguistic understanding of the user utterance. The condition of the transition.


- `conditions`

  条件（の並び）．遷移の条件を表す関数呼び出し．複数あっても構いません．複数ある場合は，`;`で連結します．各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしています．引数は0個でも構いません．各条件で使える引数については，{ref}`arguments`を参照してください．

  Condition (sequence of conditions). A function call that represents a condition for a transition. There can be more than one. If there are multiple conditions, they are concatenated with `;`. Each condition has the form `<function name>(<argument 1>, <argument 2>, ..., <argument n>)`. <argument n>)`. The number of arguments can be zero. See {ref}`arguments` for the arguments that can be used in each condition.

- `actions`

  アクション（の並び）．遷移した際に実行する関数呼び出し．複数あっても構いません．複数ある場合は，`;`で連結します．各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしています．引数は0個でも構いません．各条件で使える引数については，{ref}`arguments`を参照してください．
  Action (sequence of actions). The function call to execute when the transition occurs. There can be multiple calls. If there is more than one, they are concatenated with `;`. Each condition has the form `<function name>(<argument 1>, <argument 2>, ..., <argument n>)`. <argument n>)`. The number of arguments can be zero. See {ref}`arguments` for the arguments that can be used in each condition.


- `next state`

  遷移先の状態名
  Transition destination state name

（メモとして利用するために）シートにこれ以外のカラムがあっても構いません．
 You may have other columns on the sheet (for use as notes).

各行が表す遷移の`user utterance type`が空かもしくは言語理解結果と一致し，`conditions`が空か全部満たされた場合，遷移の条件を満たし，`next state`の状態に遷移します．その際，`actions`に書いてあるアクションが実行されます．
If the `user utterance type` of the transition represented by each line is empty or matches the result of language understanding, and if the `conditions` are empty or all of them are satisfied, the condition for the transition is satisfied and the transition is made to the `next state` state. In this case, the action described in `actions` is executed.


`state`カラムが同じ行（遷移元の状態が同じ遷移）は，上に書いてあるものから順に遷移の条件を満たしているかどうかをチェックします．
Rows with the same `state` column (transitions with the same source state) are checked to see if they satisfy the transition conditions, starting with the one written above.

デフォルト遷移（`user utterance type`カラムも`conditions`カラムも空の行）は，`state`カラムが同じ行の中で一番下に書かれていなくてはなりません．
The default transition (a line with neither `user utterance type` nor `conditions` columns empty) must have a `state` column written at the bottom of the same line.


### Special status

以下の状態名はあらかじめ定義されています．
The following state names are predefined.

- `#prep`

  準備状態．この状態がある場合，対話が始まった時（クライアントから最初にアクセスがあった時）に，この状態からの遷移が試みられます．`state`カラムの値が`#prep`の行の`conditions`にある条件がすべて満たされるかどうかを調べ，満たされた場合に，その行の`actions`のアクションを実行してから，`next state`の状態に遷移し，その状態のシステム発話が出力されます．
  Ready state. If this state exists, a transition from this state is attempted at the beginning of the dialog (when the client first accesses the server). The `state` column is checked to see if all the conditions in the `conditions` of the row with the value `#prep` are satisfied, and if so, the action in the `actions` of that row is executed, then the transition to the `next state` is made and the system speech in that state is output ...

  最初のシステム発話や状態を状況に応じて変更するときに使います．日本語サンプルアプリは，対話が行われる時間に応じて挨拶の内容を変更します．
  It is used to change the initial system utterance or state depending on the situation. The Japanese sample application changes the greeting depending on the time at which the dialog takes place.


  この準備状態はなくても構いません．
  This state of readiness is not necessary.
  
  `#prep`からの遷移先は`#initial`でなくてもよくなりました．(ver. 0.4.0)
  The destination from `#prep` does not have to be `#initial`. (ver. 0.4.0)


- `#initial`

  初期状態．`#prep`状態がない場合，対話が始まった時（クライアントから最初にアクセスがあった時）この状態から始まり，この状態のシステム発話が`output_text`に入れられてメインプロセスに返されます．
  Initial state. If there is no `#prep` state, it starts in this state when the dialog starts (when the client first accesses the system), and the system utterances in this state are put into `output_text` and returned to the main process.

  
`#prep`状態または`#initial`状態のどちらかがなくてはなりません．
There must be either `#prep` or `#initial` state.

- `#error`

  内部エラーが起きたときこの状態に移動します．システム発話を生成して終了します．
  Moves to this state when an internal error occurs. Generates a system utterance and exits.


  また，`#final_say_bye` のように，`#final`ではじまるstate IDは最終状態を表します．
最終状態ではシステム発話を生成して対話を終了します．
  A state ID beginning with `#final`, such as `#final_say_bye`, indicates the final state.
In the final state, the system generates a system utterance and terminates the dialog.



### Conditions and Actions

#### Contextual information

STN Managerは，対話のセッションごとに文脈情報を保持しています．文脈情報は変数とその値の組の集合（pythonの辞書型データ）で，値はどのようなデータ構造でも構いません．
STN Manager maintains contextual information for each dialogue session. The context information is a set of variables and their value pairs (python dictionary type data), and the values can be any data structure.


条件やアクションの関数は文脈情報にアクセスします．
Condition and action functions access contextual information.

文脈情報にはあらかじめ以下のキーと値のペアがセットされています．
The following key/value pairs are pre-set in the context information.

| キー          | 値                                                           |
| ------------- | ------------------------------------------------------------ |
| _current_state_name        | 遷移前状態の名前（文字列）
| _config       | configファイルを読み込んでできた辞書型のデータ               |
| _block_config | configファイルのうち対話管理ブロックの設定部分（辞書型のデータ） |
| _aux_data     | メインプロセスから受け取ったaux_data（辞書型のデータ） |
| _previous_system_utterance     | 直前のシステム発話（文字列） |
| _dialogue_history     | 対話履歴（リスト） |

| key | value |
| ------------- | ------------------------------------------------------------ |
| _current_state_name | name of the state before transition (string)
| _config | dictionary type data created by reading config file |
| _block_config | Configuration part of the dialog management block in the config file (dictionary type data)
| _aux_data | aux_data (data of dictionary type) received from main process
| _previous_system_utterance | previous system utterance (string)
| _dialogue_history | Dialogue history (list)



対話履歴は，以下の形です．
The dialog history is in the following form

```python
[
  {"speaker": "user",
   utterance": <正規化後のユーザ発話(文字列)>},
  {"speaker": "system",
   utterance": <システム発話>},
  {"speaker": "user",
   utterance": <正規化後のユーザ発話(文字列)>},
  {"speaker": "system",
   utterance": <システム発話>},
  ...
]
```

````python
[
  {"speaker": "user", "user".
   utterance": <user utterance after normalization (string)>},.
  {"speaker": "system", "system".
   utterance": <system utterance>},.
  {"speaker": "user", "user".
   utterance": <user utterance after normalization (string)>},.
  {"speaker": "system", "system".
   utterance": <system utterance>},.
  ...
]
````


これらに加えて新しいキーと値のペアをアクション関数内で追加することができます．
In addition to these, new key/value pairs can be added within the action function.

(arguments)=
#### Function Arguments

条件やアクションで用いる関数の引数には次のタイプがあります．
The following types of function arguments are used in conditions and actions.

- 特殊変数 （`#`で始まる文字列）
- Special variables (strings beginning with `#`)

  以下の種類があります．
  The following types are available

  - `#<スロット名>`
    直前のユーザ発話の言語理解結果（入力の`nlu_result`の値）のスロット値．スロット値が空の場合は空文字列になります．
  - `#<slot name>`.
    Slot value of the     language understanding result of the previous user utterance (the input `nlu_result` value). If the slot value is empty, it is an empty string.



  - `#<補助データのキー>`
    入力のaux_dataの中のこのキーの値．例えば`#emotion`の場合，`aux_data['emotion']`の値．このキーがない場合は，空文字列になります．
  - `#<key for auxiliary data>`.
    The value of this key in the     input aux_data. For example, in the case of `#emotion`, the value of `aux_data['emotion']`. If this key is missing, it is an empty string.


  - `#sentence`
    直前のユーザ発話（正規化したもの）
  - `#sentence`.
    Immediate previous user utterance (normalized)

  - `#user_id`
    ユーザID（文字列）
  - `#user_id`.
    User ID (string)


- 変数（`*`で始まる文字列）
- Variables (strings beginning with `*`)

  文脈情報における変数の値`*<変数名>`の形．変数の値は文字列でないといけません．文脈情報にその変数がない場合は空文字列になります．
  The value of a variable in context information in the form `*<variable name>`. The value of a variable must be a string. If the variable is not in the context information, it is an empty string.

- 変数参照（&で始まる文字列）
- Variable reference (string beginning with &)


  `&<文脈情報での変数の名前>` の形で，関数定義内で文脈情報の変数名を利用するときに用います．
  The `&&<contextual variable name>` form is used to use contextual variable names in function definitions.


- 定数（`""`で囲んだ文字列）
- Constant (string enclosed in `""`)

  文字列そのままを意味します．
  It means the string as it is.


### 関数定義
### function definition

条件やアクションで用いる関数は，DialBB組み込みのものと，開発者が定義するものがあります．条件で使う関数はbool値を返し，アクションで使う関数は何も返しません．
Functions used in conditions and actions are either built-in to DialBB or defined by the developer. Functions used in conditions return bool values, while functions used in actions return nothing.


#### 組み込み関数
#### Built-in Functions

組み込み関数には以下があります．
Built-in functions include

- 条件で用いる関数
- Functions used in conditions

  - `_eq(x, y)`

    `x`と`y`が同じなら`True`を返します．
    例：`_eq(*a, "b"`): 変数`a`の値が`"b"`なら`True`を返します．
    `_eq(#food, "ラーメン")`: `#food`スロットが`"ラーメン"`なら`True`を返します．

  - `_eq(x, y)`

    Returns `True` if `x` and `y` are the same.
    Example: `_eq(*a, "b"`): returns `True` if the value of variable `a` is `"b"`.
    `_eq(#food, "ramen")`: returns `True` if `#food` slot is `"ramen"`.


  - `_ne(x, y)`

    `x`と`y`が同じでなければ`True`を返します．

    例：`_ne(*a, *b)`: 変数`a`の値と変数`b`の値が異なれば`True`を返します．
    `_ne(#food, "ラーメン"):` `#food`スロットが`"ラーメン"`なら`False`を返します．

  - `_ne(x, y)`

    Returns `True` if `x` and `y` are not the same.

    Example: `_ne(*a, *b)`: returns `True` if the value of variable `a` is different from the value of variable `b`.
    `_ne(#food, "ramen"):` Return `False` if `#food` slot is `"ramen"`.



  - `_contains(x, y)`

    `x`が文字列として`y`を含む場合`True`を返します．  
    例：_contains(#sentence, "はい") : ユーザ発話が「はい」を含めばTrueを返します．

    Returns `True` if `x` contains `y` as a string.
    Example: contains(#sentence, "yes") : returns True if the user utterance contains "yes".


  - `_not_contains(x, y)`

    `x`が文字列として`y`を含まない場合`True`を返します．
    Returns `True` if `x` does not contain `y` as a string.

    例： `_not_contains(#sentence, "はい")` : ユーザ発話が`"はい"`を含めば`True`を返します．
    Example: `_not_contains(#sentence, "yes")` : returns `True` if the user utterance contains `"yes"`.

  - `_member_of(x, y)`

    文字列`y`を`':'`で分割してできたリストに文字列`x`が含まれていれば`True`を返します．

    例：`_member_of(#food, "ラーメン:チャーハン:餃子")`

    Returns `True` if the list formed by splitting `y` by `':'` contains the string `x`.

    Example: `_member_of(#food, "ramen:fried rice:dumplings")`


  - `_not_member_of(x, y)`

    文字列`y`を`':'`で分割してできたリストに文字列`x`が含まれていなければ`True`を返します．
    Returns `True` if the list formed by splitting `y` by `':'` does not contain the string `x`.

    例：`_not_member_of(*favorite_food, "ラーメン:チャーハン:餃子")`
    Example: `_not_member_of(*favorite_food, "ramen:fried_han:dumpling")`

- Functions used in actions

  - `_set(x, y)`

    変数`x`に`y`をセットします．
    Set `y` to the variable `x`.

    例：`_set(&a, b)`: `b`の値を`a`にセットします．
    `_set(&a, "hello")`： `a`に`"hello"`をセットします．
    Example: `_set(&a, b)`: sets the value of `b` to `a`.
    `_set(&a, "hello")`: sets `a` to `"hello"`.


  - `_set(x, y)`

    変数`x`に`y`をセットします．
    Set `y` to the variable `x`.

    例：`_set(&a, b)`: `b`の値を`a`にセットします．
    `_set(&a, "hello")`： `a`に`"hello"`をセットします．
    Example: `_set(&a, b)`: sets the value of `b` to `a`.
    `_set(&a, "hello")`: sets `a` to `"hello"`.


#### 開発者による関数定義

開発者が関数定義を行うときには，アプリケーションディレクトリのscenario_functions.pyを編集します．
When the developer defines functions, he/she edits scenario_functions.py in the application directory.

```python
def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None:
    location:str = ramen_map.get(ramen, "日本")
    context[variable] = location
```

````python
def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None: None
    location:str = ramen_map.get(ramen, "Japan")
    context[variable] = location
````

上記のように，シナリオで使われている引数にプラスして，文脈情報を受け取る辞書型の変数を必ず加える必要があります．
In addition to the arguments used in the scenario, as described above, a variable of dictionary type must be added to receive contextual information.


シナリオで使われている引数はすべて文字列でなくてはなりません．
All arguments used in the scenario must be strings.

引数には，特殊変数・変数の場合，その値が渡されます．
In the case of a special variable or variables, the value of the variable is passed as an argument.

また，変数参照の場合は'`&`'を除いた変数名が，定数の場合は，`""`の中の文字列が渡されます．
In the case of a variable reference, the variable name without the `&`' is passed, and in the case of a constant, the string in `""` is passed.


### Continuous Transition

システム発話（の1番目）が`$skip`である状態に遷移した場合，システム応答を返さず，即座に次の遷移を行います．これは，最初の遷移のアクションの結果に応じて二つ目の遷移を選択するような場合に用います．

If a transition is made to a state where the first system utterance is `$skip`, the next transition is made immediately without returning a system response. This is used in cases where the second transition is selected based on the result of the action of the first transition.


### 言語理解結果候補が複数ある場合の処理
### Processing when there are multiple candidate language comprehension results

入力の`nlu_result`がリスト型のデータで，複数の言語理解結果候補を含んでいる場合，処理は次のようになります．
If the input `nlu_result` is a list of data and contains multiple candidate language understanding results, the processing is as follows




リストの先頭から順に，言語理解結果候補の`type`の値が，現在の状態から可能な遷移のうちのどれかの`user utterance type`の値に等しいかどうかを調べ，等しい遷移があれば，その言語理解結果候補を用います．
Starting from the top of the list, check whether the `type` value of a candidate language understanding result is equal to the `user utterance type` value of one of the possible transitions from the current state, and use the candidate language understanding result if there is an equal transition.


どの言語理解結果候補も上記の条件に合わない場合，リストの先頭の言語理解結果候補を用います．
If none of the candidate language comprehension results meet the above conditions, the first language comprehension result in the list is used.

### Subdialogue

遷移先の状態名が`#gosub:<状態名1>:<状態名2>`の形の場合，`<状態名1>`の状態に遷移して，そこから始まるsubdialogueを実行します．そして，その後の対話で，遷移先が`:exit`になったら，`<状態名2>`の状態に移ります．

If the destination state name is of the form `#gosub:<state name1>:<state name2>`, it transitions to the state `<state name1>` and executes a subdialogue starting there. If the destination state is `:exit`, it moves to the state `<state name2>`.


例えば，遷移先の状態名が`#gosub:request_confirmation:confirmed`の形の場合，`request_confirmatin`から始まるsubdialogueを実行し，遷移先が`:exit`になったら，`confirmed`に戻ります．
For example, if the destination state name is of the form `#gosub:request_confirmation:confirmed`, a subdialogue starting with `request_confirmatin` is executed, and when the destination state becomes `:exit`, it returns to `confirmed`. When the destination becomes `:exit`, it returns to `confirmed`.


subdialogueの中でsubdialogueに遷移することも可能です．
It is also possible to transition to a subdialogue within a subdialogue.


### 音声入力を扱うための仕組み
### Mechanisms for handling voice input

ver. 0.4.0で，音声認識結果を入力として扱うときに生じる問題に対処するため，以下の変更が行われました．
In ver. 0.4.0, the following changes were made to address problems that occur when treating speech recognition results as input.

#### ブロックコンフィギュレーションパラメータの追加
#### Add block configuration parameters

- `input_confidence_threshold` （float．デフォルト値`1.0`）
- `input_confidence_threshold` (float; default value `1.0`)

   入力が音声認識結果の時，その確信度がこの値未満の場合に，確信度が低いとみなします．入力の確信度は，`aux_data`の`confidence`の値です．`aux_data`に`confidence`キーがないときは，確信度が高いとみなします．確信度が低い場合は，以下に述べるパラメータの値に応じて処理が変わります．
   If the input is a speech recognition result and its confidence is less than this value, it is considered low confidence. The confidence of the input is the value of `confidence` in `aux_data`. If there is no `confidence` key in `aux_data`, the confidence is considered high. In the case of low confidence, the process depends on the value of the parameter described below.
   

- `confirmation_request`（オブジェクト）
- `confirmation_request` (object)

   これは以下の形で指定します．
   This is specified in the following form.
   
   ```yaml
   confirmation_request:
     function_to_generate_utterance: <関数名（文字列）>
     acknowledgement_utterance_type: <肯定のユーザ発話タイプ名（文字列）>
     denial_utterance_type: <肯定のユーザ発話タイプ名（文字列）>
   ```

   ```yaml
   confirmation_request:.
     function_to_generate_utterance: <function name (string)
     acknowledgement_utterance_type: <user utterance type name of acknowledgement (string)
     denial_utterance_type: <name of user utterance type for affirmation (string)
   ````

   
   これが指定されている場合，入力の確信度が低いときは，状態遷移をおこなわず，`function_to_generate_utterance`で指定された関数を実行し，その返り値を発話します（確認要求発話と呼びます）．
   If this is specified, the function specified in `function_to_generate_utterance` is executed and the return value is spoken (called a confirmation request utterance), instead of making a state transition when the input is less certain.
   

   
   そして，それに対するユーザ発話に応じて次の処理を行います．
   Then, the next process is performed in response to the user's utterance.
   
   - ユーザ発話の確信度が低い時は，遷移を行わず，前の状態の発話を繰り返します．
   - When the confidence level of the user's utterance is low, the transition is not made and the previous state of utterance is repeated.

   
   - ユーザ発話のタイプが`acknowledgement_utterance_type`で指定されているものの場合，確認要求発話の前のユーザ発話に応じた遷移を行います．
   - If the type of user utterance is specified by `acknowledgement_utterance_type`, the transition is made according to the user utterance before the acknowledgement request utterance.


   
   - ユーザ発話のタイプが`denial_utterance_type`で指定されているものの場合，遷移を行わず，元の状態の発話を繰り返します．
   - If the type of user utterance is specified by `denial_utterance_type`, no transition is made and the utterance in the original state is repeated.

   
   - ユーザ発話のタイプがそれ以外の場合は，通常の遷移を行います．
   - If the user utterance type is other than that, a normal transition is performed.

   
   ただし，入力がバージイン発話の場合（`aux_data`に`barge_in`要素があり，その値が`True`の場合）はこの処理を行いません．
   However, if the input is a barge-in utterance (`aux_data` has a `barge_in` element and its value is `True`), this process is not performed.

   
   `function_to_generate_utterance`で指定する関数は，ブロックコンフィギュレーションの`function_definitions`で指定したモジュールで定義します．この関数の引数は，このブロックの入力の`nlu_result`と文脈情報です．返り値はシステム発話の文字列です．
   The function specified by `function_to_generate_utterance` is defined in the module specified by `function_definitions` in the block configuration. The arguments of the function are the `nlu_result` and context information of the block's input. The return value is a string of the system utterance.

      
   
- `utterance_to_ask_repetition`（文字列）
- `utterance_to_ask_repetition` (string)

   これが指定されている場合，入力の確信度が低いときは，状態遷移をおこなわず，この要素の値をシステム発話とします．ただし，バージインの場合（`aux_data`に`barge_in`要素があり，その値が`True`の場合）はこの処理を行いません．
   If it is specified, then when the input confidence is low, no state transition is made and the value of this element is taken as the system utterance. However, in the case of barge-in (`aux_data` has a `barge_in` element and its value is `True`), this process is not performed.

   
   
  `confirmation_request`と`utterance_to_ask_repetition`は同時に指定できません．
  The `confirmation_request` and `utterance_to_ask_repetition` cannot be specified at the same time.

      

- `ignore_out_of_context_barge_in` （ブール値．デフォルト値`False`） 
- `ignore_out_of_context_barge_in` (Boolean; must be `False` by default). Default value `False`) 

  この値が`True`の場合，入力がバージイン発話(リクエストの`aux_data`の`barge_in`の値が`True`)の場合，デフォルト遷移以外の遷移の条件を満たさなかった場合（すなわちシナリオで予想された入力ではない）か，または，入力の確信度が低い場合，遷移しません．この時に，レスポンスの`aux_data`の`barge_in_ignored`を`True`とします．
  If this value is `True`, the input is a barge-in utterance (the value of `barge_in` in the `aux_data` of the request is `True`), the conditions for a transition other than the default transition are not met (i.e. the input is not expected in the scenario), or the confidence level of the input is low the transition is not made. In this case, the `barge_in_ignored` of the response `aux_data` is set to `True`.


- `reaction_to_silence` (object)

   `action` 要素を持ちます．`action` キーの値は文字列で`repeat`か`transition`です．`action` 要素の値が`transition`の場合，`action` キーが必須です．その値は文字列です．
   It has an `action` element. The value of the `action` key is a string that can be either `repeat` or `transition`. If the value of the `action` element is `transition`, the `action` key is required. The value of the `action` key is a string.


   入力の`aux_data`が`long_silence`キーを持ちその値が`True`の場合で，かつ，デフォルト遷移以外の遷移の条件を満たさなかった場合，このパラメータに応じて以下のように動作します．
   If the input `aux_data` has a `long_silence` key and its value is `True`, and if the conditions for a transition other than the default transition are not met, then it behaves as follows, depending on this parameter


    - このパラメータが指定されていない場合，通常の状態遷移を行います．
    - If this parameter is not specified, normal state transitions are performed.

    - `action`の値が`"repeat"`の場合，状態遷移を行わず直前のシステム発話を繰り返します．
    - If the value of `action` is `"repeat"`, the previous system utterance is repeated without state transition.
	
    - `action`の値が`transition`の場合，`destination`で指定されている状態に遷移します．
    - If the value of `action` is `transition`, then the transition is made to the state specified by `destination`.

#### 組み込み条件関数の追加
#### Add built-in conditional functions

以下の組み込み条件関数が追加されています．
The following built-in conditional functions have been added

-  `_confidence_is_low()` 

   入力の`aux_data`の`confidence`の値がコンフィギュレーションの`input_confidence_threshold`の値以下の場合にTrueを返します．
   Returns True if the value of `confidence` in the    input `aux_data` is less than or equal to the value of `input_confidence_threshold` in the configuration.

   
-  `_is_long_silence()`

    入力の`aux_data`の`long_silence`の値が`True`の場合に`True`を返します．
    Returns `True` if the value of `long_silence` in the     input `aux_data` is `True`.

#### 直前の誤った入力を無視する
#### Ignore last incorrect input

入力の`aux_data`の`rewind`の値が`True`の場合，直前のレスポンスを行う前の状態から遷移を行います．
直前のレスポンスを行った際に実行したアクションによる対話文脈の変更も元に戻されます．
If the value of `rewind` in the input `aux_data` is `True`, a transition is made from the state before the last response.
Any changes to the dialog context due to actions taken during the previous response will also be undone.


音声認識の際に，ユーザ発話を間違って途中で分割してしまい，前半だけに対する応答を行ってしまった場合に用います．
This function is used when a user's speech is accidentally split in the middle during speech recognition and only the first half of the speech is responded to.

対話文脈は元に戻りますが，アクション関数の中でグローバル変数の値を変更していたり，外部データベースの内容を変更していた場合にはもとに戻らないことに注意してください．
Note that the interactive context is restored, but not if you have changed the value of a global variable in an action function or the contents of an external database.

=======
(builtin-blocks)=
# Specification of built-in block class

Built-in block classes are block classes that are included in DialBB in advance.

In ver 0.3, the canonicalization block class has been changed. In addition, a new block class for word segmentation has been introduced. The input to the SNIPS language understanding block has been changed accordingly.

Below, the explanation of the blocks that deal with only Japanese is omitted.

## Simple canonicalizer (simple string canonicalizer block)

(`dialbb.builtin_blocks.preprocess.simple_canonicalizer.SimpleCanonicalizer`)

Canonicalizes user input sentences. The main target language is English.

### Input/Output

- input
  - `input_text`: Input string (string)
    - Example: "I  like ramen".

- output (e.g. of dynamo)
  - `output_text`: string after normalization (string)
    - Example: "i like ramen".

### Description of process

Performs the following processing on the input string.

- Deletes leading and tailing spaces
- Replaces upper-case alphabetic characters by lower-case characters
- Deletes line breaks
- Converts a sequence of spaces into a single space

## Whitespace tokenizer (whitespace-based word segmentation block)

(`dialbb.builtin_blocks.tokenization.whitespace_tokenizer.WhitespaceTokenizer`)

Splits input into words separated by spaces. This is mainly for English.

### Input/Output

- input
  - `input_text`: Input string (string)
    - Example: "i like ramen".

- output (e.g. of dynamo)
  - `tokens`: list of tokens (list of strings)
    - Example: ['i','like','ramen'].
  - `tokens_with_indices`: List of token information (list of objects of class `dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`). Each token information includes the indices of start and end points in the input string.

### Description of process

Splits the input string canonicalized by the simple canonicalizer by whitespace.

## SNIPS understander (language understanding block using SNIPS)

(`dialbb.builtin_blocks.understanding_with_snips.snips_understander.Understander`)  

Determines the user utterance type (also called intent) and extracts the slots using [SNIPS_NLU](https://snips-nlu.readthedocs.io/en/latest/).

Performs language understanding in Japanese if the `language` element of the configuration is `ja`, and language understanding in English if it is `en`. 

At startup, this block reads the knowledge for language understanding written in Excel, converts it into SNIPS training data, and builds the SNIPS model.

At runtime, it uses the SNIPS model for language understanding.


### Input/Output

- input
  - `tokens`: list of tokens (list of strings)
    - Examples: ['I' 'like', 'chicken', 'salad' 'sandwiches'].
  

- output 

  - `nlu_result`: language understanding result (dict or list of dict)
    
	  - If the parameter `num_candidates` of the 	block configuration described below is 1, the language understanding result is a dictionary type in the following format.
	
	    ```json
	     {"type": <user utterance type (intent)>,. 
	      "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}
	    ```

	    The following is an example.	  

	    ```json
	     {"type": "tell-like-specific-sandwich", "slots": {"favorite-sandwich": "roast beef sandwich"}}
	    ```

	  - If `num_candidates` is greater than or equal to 2, it is a list of multiple candidate comprehension results.
	  
	    ```json
	     [{"type": <user utterance type (intent)>, 
	       "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}, ...
	      {"type": <user utterance type (intent)>,. 
	       "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}, ...
	      ....]
	    ```

### Block configuration parameters

- `knowledge_file` (string)

   Specifies the Excel file that describes the knowledge. The file path must be relative to the directory where the configuration file is located.

- `function_definitions`(string)


   Specifies the name of the module that defines the dictionary functions (see {ref}`dictionary_function`). If there are multiple modules, connect them with `':'`. The module must be in the module search path. (The directory of the configuration file is in the module search path.)

- `flags_to_use`(list of strings)

   Specifies the flags to be used. If one of these values is written in the `flag` column of each sheet, it is read. If this parameter is not set, all rows are read.

- `canonicalizer` 

   Specifies the canonicalization information to be performed when converting language comprehension knowledge to SNIPS training data.

   - `class`
   
      Specifies the class of the normalization block. Basically, the same normalization block used in the application is specified.


- `tokenizer` 

   Specifies the tokenization information to be used when converting language understanding knowledge to SNIPS training data.

   - `class`
   
      Specifies the class of the tokenization block. Basically, the same tokenization block used in the application is specified.

	  
- `num_candidates` (Integer. Default value `1`)

   Specifies the maximum number of language understanding results (n for n-best).

- `knowledge_google_sheet` (hash)

  - Excelの代わりにGoogle Sheetを用いる場合の情報を記述します．（Google Sheetを利用する際の設定は[こはたさんの記事](https://note.com/kohaku935/n/nc13bcd11632d)が参考になりますが，Google Cloud Platformの設定画面のUIがこの記事とは多少変わっています．）

  - This includes information for using Google Sheet instead of Excel.
  
    - `sheet_id` (string)

      Google Sheet ID.

    - `key_file`(string)
 
       Specify the key file to access the Goole Sheet API as a relative path from the configuration file directory.

(nlu_knowledge)=

### Language Understanding Knowledge

Language understanding knowledge consists of the following four sheets.

| sheet name | contents |
| ---------- | -------------------------------------- |
| utterances | examples of utterances by type |
| slots | relationship between slots and entities |
| entities | Information about entities |
| dictionary | dictionary entries and synonyms per entity |

The sheet name can be changed in the block configuration, but since it is unlikely to be changed, a detailed explanation is omitted.

#### utterances sheet

Each row consists of the following columns

- `flag`      

   Flags to be used or not. Y: yes, T: test, etc. are often written. Which flag's rows to use is specified in the configuration. In the configuration of the sample application, all lines are set to be used.


   利用するかどうかを決めるフラグ．Y: yes, T: testなどを書くことが多いです．どのフラグの行を利用するかはコンフィギュレーションに記述します．サンプルアプリのコンフィギュレーションでは，すべての行を使う設定になっています． 

- `type`     

   発話のタイプ（インテント）                         

- `utterance` 

   発話例．スロットを`(豚骨ラーメン)[favorite_ramen]が好きです`のように`(<スロットに対応する言語表現>)[<スロット名>]`で表現します．スロットに対応する言語表現＝言語理解結果に表れる（すなわちmanagerに送られる）スロット値ではないことに注意．言語表現が`dictionary`シートの`synonyms`カラムにあるものの場合，スロット値は，`dictionary`シートの`entity`カラムに書かれたものになります． 

utterancesシートのみならずこのブロックで使うシートにこれ以外のカラムがあっても構いません．

#### slotsシート

各行は次のカラムからなります．

- `flag`

  utterancesシートと同じ

- `slot name` 

  スロット名．utterancesシートの発話例で使うもの．言語理解結果でも用います．

- `entity class`

  エンティティクラス名．スロットの値がどのようなタイプの名詞句なのかを表します．異なるスロットが同じエンティティクラスを持つ場合があります．例えば，`(東京)[source_station]から(京都)[destination_station]までの特急券を買いたい`のように，`source_station, destination_station`とも`station`クラスのエンティティを取ります．
  `entity class`カラムの値として辞書関数（`dialbb/<関数名>`の形）を使うことができます．これにより，dictionaryシートに辞書情報を記述する代わりに，関数呼び出しで辞書記述を得ることができます．（例: `dialbb/location`）関数は以下の「{ref}`dictionary_function`」で説明します．
  またentity classカラムの値は，SNIPSの[builtin entity](https://snips-nlu.readthedocs.io/en/latest/builtin_entities.html)でも構いません．（例: `snips/city`）

  SNIPSのbuiltin entityを用いる場合，以下のようにしてインストールする必要があります．

```sh
	$ snips-nlu download-entity snips/city ja
```

​	SNIPSのbuiltin entityを用いた場合の精度などの検証は不十分です．

#### entitiesシート

各行は次のカラムからなります．

- `flag`

   utterancesシートと同じ

- `entity class`

  エンティティクラス名．slotsシートで辞書関数を指定した場合は，こでも同じように辞書関数名を書く必要があります．

- `use synonyms`

  [同義語を使うかどうか](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#entity-values-synonyms) (`Yes`または`No`)

- `automatically extensible`

  [辞書にない値でも認識するかどうか](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#auto-extensible) (`Yes`または`No`)

- `matching strictness`

  [エンティティのマッチングの厳格さ](https://snips-nlu.readthedocs.io/en/latest/api.html) `0.0` - `1.0`

#### dictionaryシート

各行は次のカラムからなります．

- `flag`

  utterancesシートと同じ

- `entity class`

   エンティティクラス名

- `entity`

   辞書エントリー名．言語理解結果にも含まれます．

- `synonyms`

   同義語を`,`または `，`または`，`で連結したもの

(dictionary_function)=
#### 開発者による辞書関数の定義

辞書関数は，主に外部のデータベースなどから辞書情報を取ってくるときに利用します．

辞書関数はブロックコンフィギュレーションの`dictionary_function`で指定するモジュールの中で定義します．

辞書関数は引数にコンフィギュレーションとブロックコンフィギュレーションを取ります．これらに外部データベースへの接続情報などが書いてあることを想定しています．

辞書関数の返り値は辞書型のリストで，`{"value": <文字列>, "synonyms": <文字列のリスト>}`の形の辞書型のリストです．`"synonyms"`キーはなくても構いません．

以下に辞書関数の例を示します．

```python
def location(config: Dict[str, Any], block_config: Dict[str, Any]) \
    -> List[Dict[str, Union[str, List[str]]]]:
    return [{"value": "札幌", "synonyms": ["さっぽろ", "サッポロ"]},
            {"value": "荻窪", "synonyms": ["おぎくぼ"]},
            {"value": "徳島"}]
```

#### SNIPSの訓練データ

アプリを立ち上げると上記の知識はSNIPSの訓練データに変換され，モデルが作られます．

SNIPSの訓練データはアプリのディレクトリの`_training_data.json`です．このファイルを見ることで，うまく変換されているかどうかを確認できます．

(stn_manager)=
## STN manager （状態遷移ネットワークベースの対話管理ブロック）

(`dialbb.builtin_blocks.stn_manager.stn_management`)  

状態遷移ネットワーク(State-Transition Network)を用いて対話管理を行います．

- 入力
  - `sentence`: 正規化後のユーザ発話（文字列）
  - `nlu_result`:言語理解結果（辞書型または辞書型のリスト）
  - `user_id`: ユーザID（文字列）
  - `aux_data`: 補助データ（辞書型）（必須ではありませんが指定することが推奨されます）
- 出力
  - `output_text`: システム発話（文字列）
     例：
	  ```
	  "醤油ラーメン好きなんですね"
	  ```
  - `final`: 対話終了かどうかのフラグ（ブール値）
  - `aux_data`: 補助データ（辞書型）(ver. 0.4.0で変更）
     入力の補助データを，後述のアクション関数の中でアップデートしたものに，遷移した状態のIDを含めたもの．アクション関数の中でのアップデートは必ずしも行われるわけではない．遷移した状態は，以下の形式で付加される．
     ```json
	 {"state": "特定のラーメンが好き"}
     ```
     
### ブロックコンフィギュレーションのパラメータ

- `knowledge_file`（文字列）

  シナリオを記述したExcelファイルを指定します．コンフィギュレーションファイルのあるディレクトリからの相対パスで記述します．

- `function_definitions`（文字列）

  シナリオ関数（{ref}`dictionary_function`を参照）を定義したモジュールの名前です．複数ある場合は`':'`でつなぎます．モジュール検索パスにある必要があります．（コンフィギュレーションファイルのあるディレクトリはモジュール検索パスに入っています．）

- `flags_to_use`（文字列のリスト）

  各シートの`flag`カラムにこの値のうちのどれかが書かれていた場合に読み込みます．

- `knowledge_google_sheet` (ハッシュ)

  SNIPS Understanderと同じです．

- `scenario_graph`: (ブール値．デフォルト値`False`）

   この値が`True`の場合，シナリオシートの`system utterance`カラムと`user utterance example`カラムの値を使って，グラフを作成します．これにより，シナリオ作成者が直感的に状態遷移ネットワークを確認できます．
   
- `repeat_when_no_available_transitions` （ブール値．デフォルト値`False`．ver. 0.4.0で追加）

   この値が`True`のとき，デフォルト遷移（後述）以外の遷移で条件に合う遷移がないとき，遷移せず同じ発話を繰り返します．

(scenario)=
### 対話管理の知識記述

対話管理知識（シナリオ）は，Excelファイルのscenarioシートです．

このシートの各行が，一つの遷移を表します．各行は次のカラムからなります．

- `flag`

  utteranceシートと同じ

- `state`

  遷移元の状態名

- `system utterance`

  `state`の状態で生成されるシステム発話の候補．システム発話文字列に含まれる{<変数>}は，対話中にその変数に代入された値で置き換えられます．`state`が同じ行は複数あり得ますが，同じ`state`の行の`system utterance`すべてが発話の候補となり，ランダムに生成されます．

- `user utterance example`

  ユーザ発話の例．対話の流れを理解するために書くだけで，システムでは用いられません．

- `user utterance type`

  ユーザ発話を言語理解した結果得られるユーザ発話のタイプ．遷移の条件となります．

- `conditions`

  条件（の並び）．遷移の条件を表す関数呼び出し．複数あっても構いません．複数ある場合は，`;`で連結します．各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしています．引数は0個でも構いません．各条件で使える引数については，{ref}`arguments`を参照してください．

- `actions`

  アクション（の並び）．遷移した際に実行する関数呼び出し．複数あっても構いません．複数ある場合は，`;`で連結します．各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしています．引数は0個でも構いません．各条件で使える引数については，{ref}`arguments`を参照してください．

- `next state`

  遷移先の状態名

（メモとして利用するために）シートにこれ以外のカラムがあっても構いません．

各行が表す遷移の`user utterance type`が空かもしくは言語理解結果と一致し，`conditions`が空か全部満たされた場合，遷移の条件を満たし，`next state`の状態に遷移します．その際，`actions`に書いてあるアクションが実行されます．

`state`カラムが同じ行（遷移元の状態が同じ遷移）は，上に書いてあるものから順に遷移の条件を満たしているかどうかをチェックします．

デフォルト遷移（`user utterance type`カラムも`conditions`カラムも空の行）は，`state`カラムが同じ行の中で一番下に書かれていなくてはなりません．


### 特別な状態

以下の状態名はあらかじめ定義されています．

- `#prep`

  準備状態．この状態がある場合，対話が始まった時（クライアントから最初にアクセスがあった時）に，この状態からの遷移が試みられます．`state`カラムの値が`#prep`の行の`conditions`にある条件がすべて満たされるかどうかを調べ，満たされた場合に，その行の`actions`のアクションを実行してから，`next state`の状態に遷移し，その状態のシステム発話が出力されます．

  最初のシステム発話や状態を状況に応じて変更するときに使います．日本語サンプルアプリは，対話が行われる時間に応じて挨拶の内容を変更します．

  この準備状態はなくても構いません．
  
  `#prep`からの遷移先は`#initial`でなくてもよくなりました．(ver. 0.4.0)

- `#initial`

  初期状態．`#prep`状態がない場合，対話が始まった時（クライアントから最初にアクセスがあった時）この状態から始まり，この状態のシステム発話が`output_text`に入れられてメインプロセスに返されます．
  
`#prep`状態または`#initial`状態のどちらかがなくてはなりません．

- `#error`

  内部エラーが起きたときこの状態に移動します．システム発話を生成して終了します．

また，`#final_say_bye` のように，`#final`ではじまるstate IDは最終状態を表します．
最終状態ではシステム発話を生成して対話を終了します．


### 条件とアクション

#### 文脈情報

STN Managerは，対話のセッションごとに文脈情報を保持しています．文脈情報は変数とその値の組の集合（pythonの辞書型データ）で，値はどのようなデータ構造でも構いません．

条件やアクションの関数は文脈情報にアクセスします．

文脈情報にはあらかじめ以下のキーと値のペアがセットされています．

| キー          | 値                                                           |
| ------------- | ------------------------------------------------------------ |
| _current_state_name        | 遷移前状態の名前（文字列）
| _config       | configファイルを読み込んでできた辞書型のデータ               |
| _block_config | configファイルのうち対話管理ブロックの設定部分（辞書型のデータ） |
| _aux_data     | メインプロセスから受け取ったaux_data（辞書型のデータ） |
| _previous_system_utterance     | 直前のシステム発話（文字列） |
| _dialogue_history     | 対話履歴（リスト） |


対話履歴は，以下の形です．

```python
[
  {"speaker": "user",
   utterance": <正規化後のユーザ発話(文字列)>},
  {"speaker": "system",
   utterance": <システム発話>},
  {"speaker": "user",
   utterance": <正規化後のユーザ発話(文字列)>},
  {"speaker": "system",
   utterance": <システム発話>},
  ...
]
```


これらに加えて新しいキーと値のペアをアクション関数内で追加することができます．

(arguments)=

#### 関数の引数

条件やアクションで用いる関数の引数には次のタイプがあります．

- 特殊変数 （`#`で始まる文字列）

  以下の種類があります．

  - `#<スロット名>`
    直前のユーザ発話の言語理解結果（入力の`nlu_result`の値）のスロット値．スロット値が空の場合は空文字列になります．
  - `#<補助データのキー>`
    入力のaux_dataの中のこのキーの値．例えば`#emotion`の場合，`aux_data['emotion']`の値．このキーがない場合は，空文字列になります．
  - `#sentence`
    直前のユーザ発話（正規化したもの）
  - `#user_id`
    ユーザID（文字列）

- 変数（`*`で始まる文字列）

  文脈情報における変数の値`*<変数名>`の形．変数の値は文字列でないといけません．文脈情報にその変数がない場合は空文字列になります．

- 変数参照（&で始まる文字列）

  `&<文脈情報での変数の名前>` の形で，関数定義内で文脈情報の変数名を利用するときに用います．

- 定数（`""`で囲んだ文字列）

  文字列そのままを意味します．


### 関数定義

条件やアクションで用いる関数は，DialBB組み込みのものと，開発者が定義するものがあります．条件で使う関数はbool値を返し，アクションで使う関数は何も返しません．

#### 組み込み関数

組み込み関数には以下があります．

- 条件で用いる関数

  - `_eq(x, y)`

    `x`と`y`が同じなら`True`を返します．
    例：`_eq(*a, "b"`): 変数`a`の値が`"b"`なら`True`を返します．
    `_eq(#food, "ラーメン")`: `#food`スロットが`"ラーメン"`なら`True`を返します．

  - `_ne(x, y)`

    `x`と`y`が同じでなければ`True`を返します．

    例：`_ne(*a, *b)`: 変数`a`の値と変数`b`の値が異なれば`True`を返します．
    `_ne(#food, "ラーメン"):` `#food`スロットが`"ラーメン"`なら`False`を返します．

  - `_contains(x, y)`

    `x`が文字列として`y`を含む場合`True`を返します．  
    例：_contains(#sentence, "はい") : ユーザ発話が「はい」を含めばTrueを返します．

  - `_not_contains(x, y)`

    `x`が文字列として`y`を含まない場合`True`を返します．

    例： `_not_contains(#sentence, "はい")` : ユーザ発話が`"はい"`を含めば`True`を返します．

  - `_member_of(x, y)`

    文字列`y`を`':'`で分割してできたリストに文字列`x`が含まれていれば`True`を返します．

    例：`_member_of(#food, "ラーメン:チャーハン:餃子")`

  - `_not_member_of(x, y)`

    文字列`y`を`':'`で分割してできたリストに文字列`x`が含まれていなければ`True`を返します．

    例：`_not_member_of(*favorite_food, "ラーメン:チャーハン:餃子")`


- アクションで用いる関数

  - `_set(x, y)`

    変数`x`に`y`をセットします．

    例：`_set(&a, b)`: `b`の値を`a`にセットします．
    `_set(&a, "hello")`： `a`に`"hello"`をセットします．

  - `_set(x, y)`

    変数`x`に`y`をセットします．

    例：`_set(&a, b)`: `b`の値を`a`にセットします．
    `_set(&a, "hello")`： `a`に`"hello"`をセットします．

#### 開発者による関数定義

開発者が関数定義を行うときには，アプリケーションディレクトリのscenario_functions.pyを編集します．

```python
def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None:
    location:str = ramen_map.get(ramen, "日本")
    context[variable] = location
```

上記のように，シナリオで使われている引数にプラスして，文脈情報を受け取る辞書型の変数を必ず加える必要があります．

シナリオで使われている引数はすべて文字列でなくてはなりません．

引数には，特殊変数・変数の場合，その値が渡されます．

また，変数参照の場合は'`&`'を除いた変数名が，定数の場合は，`""`の中の文字列が渡されます．


### 連続遷移

システム発話（の1番目）が`$skip`である状態に遷移した場合，システム応答を返さず，即座に次の遷移を行います．これは，最初の遷移のアクションの結果に応じて二つ目の遷移を選択するような場合に用います．

### 言語理解結果候補が複数ある場合の処理

入力の`nlu_result`がリスト型のデータで，複数の言語理解結果候補を含んでいる場合，処理は次のようになります．

リストの先頭から順に，言語理解結果候補の`type`の値が，現在の状態から可能な遷移のうちのどれかの`user utterance type`の値に等しいかどうかを調べ，等しい遷移があれば，その言語理解結果候補を用います．

どの言語理解結果候補も上記の条件に合わない場合，リストの先頭の言語理解結果候補を用います．

### Subdialogue

遷移先の状態名が`#gosub:<状態名1>:<状態名2>`の形の場合，`<状態名1>`の状態に遷移して，そこから始まるsubdialogueを実行します．そして，その後の対話で，遷移先が`:exit`になったら，`<状態名2>`の状態に移ります．

例えば，遷移先の状態名が`#gosub:request_confirmation:confirmed`の形の場合，`request_confirmatin`から始まるsubdialogueを実行し，遷移先が`:exit`になったら，`confirmed`に戻ります．

subdialogueの中でsubdialogueに遷移することも可能です．


### 音声入力を扱うための仕組み

ver. 0.4.0で，音声認識結果を入力として扱うときに生じる問題に対処するため，以下の変更が行われました．

#### ブロックコンフィギュレーションパラメータの追加

- `input_confidence_threshold` （float．デフォルト値`1.0`）

   入力が音声認識結果の時，その確信度がこの値未満の場合に，確信度が低いとみなします．入力の確信度は，`aux_data`の`confidence`の値です．`aux_data`に`confidence`キーがないときは，確信度が高いとみなします．確信度が低い場合は，以下に述べるパラメータの値に応じて処理が変わります．
   
- `confirmation_request`（オブジェクト）

   これは以下の形で指定します．
   
   ```yaml
   confirmation_request:
     function_to_generate_utterance: <関数名（文字列）>
     acknowledgement_utterance_type: <肯定のユーザ発話タイプ名（文字列）>
     denial_utterance_type: <肯定のユーザ発話タイプ名（文字列）>
   ```
   
   これが指定されている場合，入力の確信度が低いときは，状態遷移をおこなわず，`function_to_generate_utterance`で指定された関数を実行し，その返り値を発話します（確認要求発話と呼びます）．
   
   そして，それに対するユーザ発話に応じて次の処理を行います．
   
   - ユーザ発話の確信度が低い時は，遷移を行わず，前の状態の発話を繰り返します．
   
   - ユーザ発話のタイプが`acknowledgement_utterance_type`で指定されているものの場合，確認要求発話の前のユーザ発話に応じた遷移を行います．
   
   - ユーザ発話のタイプが`denial_utterance_type`で指定されているものの場合，遷移を行わず，元の状態の発話を繰り返します．
   
   - ユーザ発話のタイプがそれ以外の場合は，通常の遷移を行います．
   
   ただし，入力がバージイン発話の場合（`aux_data`に`barge_in`要素があり，その値が`True`の場合）はこの処理を行いません．
   
   `function_to_generate_utterance`で指定する関数は，ブロックコンフィギュレーションの`function_definitions`で指定したモジュールで定義します．この関数の引数は，このブロックの入力の`nlu_result`と文脈情報です．返り値はシステム発話の文字列です．
      
   
- `utterance_to_ask_repetition`（文字列）

   これが指定されている場合，入力の確信度が低いときは，状態遷移をおこなわず，この要素の値をシステム発話とします．ただし，バージインの場合（`aux_data`に`barge_in`要素があり，その値が`True`の場合）はこの処理を行いません．
   
  `confirmation_request`と`utterance_to_ask_repetition`は同時に指定できません．
      

- `ignore_out_of_context_barge_in` （ブール値．デフォルト値`False`） 

  この値が`True`の場合，入力がバージイン発話(リクエストの`aux_data`の`barge_in`の値が`True`)の場合，デフォルト遷移以外の遷移の条件を満たさなかった場合（すなわちシナリオで予想された入力ではない）か，または，入力の確信度が低い場合，遷移しません．この時に，レスポンスの`aux_data`の`barge_in_ignored`を`True`とします．

- `reaction_to_silence` （オブジェクト）

   `action` 要素を持ちます．`action` キーの値は文字列で`repeat`か`transition`です．`action` 要素の値が`transition`の場合，`action` キーが必須です．その値は文字列です．

   入力の`aux_data`が`long_silence`キーを持ちその値が`True`の場合で，かつ，デフォルト遷移以外の遷移の条件を満たさなかった場合，このパラメータに応じて以下のように動作します．

    - このパラメータが指定されていない場合，通常の状態遷移を行います．

    - `action`の値が`"repeat"`の場合，状態遷移を行わず直前のシステム発話を繰り返します．
	
    - `action`の値が`transition`の場合，`destination`で指定されている状態に遷移します．

#### 組み込み条件関数の追加

以下の組み込み条件関数が追加されています．

-  `_confidence_is_low()` 

   入力の`aux_data`の`confidence`の値がコンフィギュレーションの`input_confidence_threshold`の値以下の場合にTrueを返します．

   
-  `_is_long_silence()`

    入力の`aux_data`の`long_silence`の値が`True`の場合に`True`を返します．

#### 直前の誤った入力を無視する

入力の`aux_data`の`rewind`の値が`True`の場合，直前のレスポンスを行う前の状態から遷移を行います．
直前のレスポンスを行った際に実行したアクションによる対話文脈の変更も元に戻されます．

音声認識の際に，ユーザ発話を間違って途中で分割してしまい，前半だけに対する応答を行ってしまった場合に用います．

対話文脈は元に戻りますが，アクション関数の中でグローバル変数の値を変更していたり，外部データベースの内容を変更していた場合にはもとに戻らないことに注意してください．









>>>>>>> 92c01e55fea3ce434d88aec76045148473ec4524
