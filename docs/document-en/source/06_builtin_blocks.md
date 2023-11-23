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

  - This specfies information for using Google Sheet instead of Excel.
  
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

   Example utterance. Each slot is annotated as  `(<linguistic expression corresponding to the slot>)[<slot name>]`, as in `(I like (chiken salad sandwiches)[favorite_sandwich]. Note that the linguistic expression corresponding to a slot does not always equal to the slot value that appears in the language understanding result (i.e., is sent to manager). If the linguistic expression eauals to the `synonyms` column of the `dictionary` sheet, the slot value will be the value of the `entity` column of the `dictionary` sheet.

The sheets that this block uses, including the utterance sheets, can have other columns than these.

#### slots sheet

Each row consists of the following columns.

- `flag`

  Same as on the utterance sheet.

- `slot name` 

  Slot name. It is used in the example utterances in the utterances sheet. Also used in the language understanding results.

- `entity class`

  Entity class name. This indicates what type of noun phrase the slot value is. Different slots may have the same entity class. For example, `I want to buy an express ticket from (Tokyo)[source_station] to (Kyoto)[destination_station]`, both `source_station, destination_station` have entity of class `station`. 

  You can use a dictionary function (of the form `dialbb/<function name>`) as the value of the   `entity class` column. This allows you to obtain a dictionary description with a function call instead of writing the dictionary information on a dictionary sheet (e.g. `dialbb/location`). （The function (e.g. `dialbb/location`) is described in "{ref}`dictionary_function`" below.

  The value of the entity class column can also be a SNIPS [builtin entity](https://snips-nlu.readthedocs.io/en/latest/builtin_entities.html). (e.g. `snips/city`)

  When you use SNIPS builtin entities, you need to install it as follows

```sh
	$ snips-nlu download-entity snips/city en
```

    Accuracy and other aspects of the SNIPS builtin entities have not been fully verified.

#### entities sheet

Each row consists of the following columns

- `flag`

   Same as on the utterance sheet.

- `entity class`

   Entity class name. If a dictionary function is specified in the slots sheet, the same dictionary function name must be written here.

- `use synonyms`

  [Whether to use synonyms or not](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#entity-values-synonyms) (`Yes` or `No`)

- `automatically extensible`

  [Whether to recongize values not in dictionary or not](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#auto-extensible) (`Yes` or `No`)

- `matching strictness`

  [Strictness of matching entities](https://snips-nlu.readthedocs.io/en/latest/api.html) `0.0` - `1.0`.


#### dictionary sheet

Each row consists of the following columns

- `flag`

  Same as that of the utterance sheet.

- `entity class`

   entity class name.

- `entity`

   The name of the dictionary entry. It is also included in language understanding results.

- `synonyms`

   Synonyms joined by `,` or `, ` or `, `

(dictionary_function)=
#### Dictionary function definitions by developers

Dictionary functions are mainly used to retrieve dictionary information from external databases.

Dictionary functions are defined in the module specified by `dictionary_function` in the block configuration.

The dictionary function takes configuration and block configuration as arguments. It is assumed that the these contain connection information to external databases.

The return value of a dictionary function is a list of dicts of the form `{"value": <string>, "synonyms": <list of strings>}`. The ``synonyms"`` key is optional.

Examples of dictionary functions are shown below.


````python
def location(config: Dict[str, Any], block_config: Dict[str, Any]) \
    -> List[Dict[str, Union[str, List[str]]]]:.
    return [{"value": "US", "synonyms": ["USA", "America"]}, }
            {"value": "Ogikubo", "synonyms": ["ogikubo"]},.
            {"value": "Tokushima"}]
````


#### SNIPS training data

When the application is launched, the above knowledge is converted into SNIPS training data and a model is created.

The SNIPS training data is `_training_data.json` in the application directory. By looking at this file, you can check if the conversion is successful.

(stn_manager)=
## STN manager (state transition network-based dialogue management block)

(`dialbb.builtin_blocks.stn_manager.stn_management`)  

It perfomrs dialogue management using a state-transition neetwork.

- input
  - `sentence`: User utterance after canonicalization (string)
  - `nlu_result`: language understanding result (dictionary or list of dictionary)
  - `user_id`: user ID (string)
  - `aux_data`: auxiliary data (dictionary type) (not required, but specifying this is recommended)


- output 

  - `output_text`: system utterance (string)

     Example:
	  ````
	  "So you like chiken salad sandwiches."
	  ````
  - `final`: a flag indicating whether the dialog is finished or not. (bool)

  - `aux_data`: auxiliary data (dictionary type) 

     The auxiliary data of the input is updated in the action function described below, including the ID of the transitioned state. Updates are not necessarily performed in the action function. The transitioned state is added in the following format.

     ```json
	 {"state": "I like a particular ramen" }
     ```
     
### Block configuration parameters

- `knowledge_file` (string)

  Specifies an Excel file describing the scenario. It is a relative path from the directory wherer  the configuration file exists.

- `function_definitions` (string)

  The name of the module that defines the scenario function (see {ref}`dictionary_function`). If there are multiple modules, connect them with `':'`. The module must be in the Python module search path. (The directory containing the configuration file is in the module search path.)

- `flags_to_use` (list of strings)

  Same as the SNIPS Understander.

- `knowledge_google_sheet` (object)

  Same as the SNIPS Understander.

- `scenario_graph`: (boolean. Default value is `False`)

   If this value is `True`, the values in the `system utterance` and `user utterance example` columns of the scenario sheet are used to create the graph. This allows the scenario writer to intuitively see the state transition network.

   
- `repeat_when_no_available_transitions` (Boolean. Default value is `False`)

   When this value is `True`, if there is no transition other than the default transition (see below) that matches the condition, the same utterance is repeated without transition.

(scenario)=
### Dialogue Management Knowledge Description

The dialog management knowledge (scenario) is written in the scenario sheet in the Excel file.

Each row of the sheet represents a transition. Each row consists of the following columns

- `flag`

  Same as on the utterances sheet.

- `state`

  The name of the source state of the transition.

- `system utterance`

    Candidates of the system utterance generated in the `state` state. The {<variable>} in the system utterance string is replaced by the value assigned to the variable during the dialogue. There can be multiple lines with the same `state`, but all `system utterance` in the lines having the same `state` become system utterance candidates, and will be chosen randomely.

- `user utterance example`

  Example of user utterance. It is only written to understand the flow of the dialogue, and is not used by the system.

- `user utterance type`

  The user utterance type obtained by language understanding. It is used as a condition of the transition.


- `conditions`

  Condition (sequence of conditions). A function call that represents a condition for a transition. There can be more than one. If there are multiple conditions, they are concatenated with `;`. Each condition has the form `<function name>(<argument 1>, <argument 2>, ..., <argument n>)`. <argument n>)`. The number of arguments can be zero. See {ref}`arguments` for the arguments that can be used in each condition.

- `actions`

  アクション（の並び）．遷移した際に実行する関数呼び出し．複数あっても構いません．複数ある場合は，`;`で連結します．各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしています．引数は0個でも構いません．各条件で使える引数については，{ref}`arguments`を参照してください．

  A sequece of actions, which are function calls to execute when the transition occurs. If there is more than one, they are concatenated with `;`. Each condition has the form `<function name>(<argument 1>, <argument 2>, ..., <argument n>)`. <argument n>)`. The number of arguments can be zero. See {ref}`arguments` for the arguments that can be used in each condition.


- `next state`

  The name of the destination state of the transition

  There can be other columns on this sheet (for use as notes).

各行が表す遷移の`user utterance type`が空かもしくは言語理解結果と一致し，`conditions`が空か全部満たされた場合，遷移の条件を満たし，`next state`の状態に遷移します．その際，`actions`に書いてあるアクションが実行されます．
If the `user utterance type` of the transition represented by each line is empty or matches the result of language understanding, and if the `conditions` are empty or all of them are satisfied, the condition for the transition is satisfied and the transition is made to the `next state` state. In this case, the action described in `actions` is executed.


`state`カラムが同じ行（遷移元の状態が同じ遷移）は，上に書いてあるものから順に遷移の条件を満たしているかどうかをチェックします．
Rows with the same `state` column (transitions with the same source state) are checked to see if they satisfy the transition conditions, starting with the one written above.

デフォルト遷移（`user utterance type`カラムも`conditions`カラムも空の行）は，`state`カラムが同じ行の中で一番下に書かれていなくてはなりません．
The default transition (a line with neither `user utterance type` nor `conditions` columns empty) must have a `state` column written at the bottom of the same line.


### Special status

The following state names are predefined.

- `#prep`

  準備状態．この状態がある場合，対話が始まった時（クライアントから最初にアクセスがあった時）に，この状態からの遷移が試みられます．`state`カラムの値が`#prep`の行の`conditions`にある条件がすべて満たされるかどうかを調べ，満たされた場合に，その行の`actions`のアクションを実行してから，`next state`の状態に遷移し，その状態のシステム発話が出力されます．

  Preperation state. If this state exists, a transition from this state is attempted at the beginning of the dialog (when the client first accesses the server). The `state` column is checked to see if all the conditions in the `conditions` of the row with the value `#prep` are satisfied, and if so, the action in the `actions` of that row is executed, then the transition to the `next state` is made and the system speech in that state is output ...

  最初のシステム発話や状態を状況に応じて変更するときに使います．日本語サンプルアプリは，対話が行われる時間に応じて挨拶の内容を変更します．

  It is used to change the initial system utterance or state depending on the situation. The Japanese sample application changes the greeting depending on the time at which the dialog takes place.

  This state is not necessary.
  
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


Condition and action functions access contextual information.

文脈情報にはあらかじめ以下のキーと値のペアがセットされています．

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



The dialog history is in the following form.

````python
[
  {"speaker": "user", "user".
   utterance": <canonicalized user utterance (string)>},.
  {"speaker": "system", "system".
   utterance": <canonicalized user utterance (string)>},.
  {"speaker": "user", "user".
   utterance": <canonicalized user utterance (string)>},.
  ...
]
````

In addition to these, new key/value pairs can be added within the action function.

(arguments)=
#### Function Arguments

The arguments of the functions used in conditions and actions are of the following types.


- Special variables (strings beginning with `#`)

  The following types are available

  - `#<slot name>`
    直前のユーザ発話の言語理解結果（入力の`nlu_result`の値）のスロット値．スロット値が空の場合は空文字列になります．
    Slot value of the     language understanding result of the previous user utterance (the input `nlu_result` value). If the slot value is empty, it is an empty string.



  - `#<key for auxiliary data>`
    入力のaux_dataの中のこのキーの値．例えば`#emotion`の場合，`aux_data['emotion']`の値．このキーがない場合は，空文字列になります．

    The value of this key in the     input aux_data. For example, in the case of `#emotion`, the value of `aux_data['emotion']`. If this key is missing, it is an empty string.


  - `#sentence`
    直前のユーザ発話（正規化したもの）
    Immediate previous user utterance (normalized)

  - `#user_id`
    User ID (string)


- Variables (strings beginning with `*`)

  文脈情報における変数の値`*<変数名>`の形．変数の値は文字列でないといけません．文脈情報にその変数がない場合は空文字列になります．
  The value of a variable in context information in the form `*<variable name>`. The value of a variable must be a string. If the variable is not in the context information, it is an empty string.

- 変数参照（&で始まる文字列）
- Variable reference (string beginning with &)


  `&<文脈情報での変数の名前>` の形で，関数定義内で文脈情報の変数名を利用するときに用います．
  The `&&<contextual variable name>` form is used to use contextual variable names in function definitions.


- Constant (string enclosed in `""`)

  It means the string as it is.


### Function Definitions

Functions used in conditions and actions are either built-in to DialBB or defined by the developers.A function used in a condition returns boolean values, while a function used in an action returns nothing.


#### Built-in Functions

The built-in functions are as follows:

- Functions used in conditions

  - `_eq(x, y)`

    Returns `True` if `x` and `y` are the same.
    e.g.,  `_eq(*a, "b"`): returns `True` if the value of variable `a` is `"b"`.
    `_eq(#food, "ramen")`: returns `True` if `#food` slot value is `"ramen"`.

  - `_ne(x, y)`

    Returns `True` if `x` and `y` are not the same.

e of variable `b`.
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

    Set `y` to the variable `x`.

    例：`_set(&a, b)`: `b`の値を`a`にセットします．
    `_set(&a, "hello")`： `a`に`"hello"`をセットします．
    Example: `_set(&a, b)`: sets the value of `b` to `a`.
    `_set(&a, "hello")`: sets `a` to `"hello"`.


  - `_set(x, y)`

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


### Process in the case where there are multiple language understanding results

If the input `nlu_result` is a list that contains multiple language understanding results, the process is as follows

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

      
   
- `utterance_to_ask_repetition` (string)

   これが指定されている場合，入力の確信度が低いときは，状態遷移をおこなわず，この要素の値をシステム発話とします．ただし，バージインの場合（`aux_data`に`barge_in`要素があり，その値が`True`の場合）はこの処理を行いません．

   If it is specified, then when the input confidence is low, no state transition is made and the value of this element is taken as the system utterance. However, in the case of barge-in (`aux_data` has a `barge_in` element and its value is `True`), this process is not performed.

   
   
  `confirmation_request` and `utterance_to_ask_repetition` cannot be specified at the same time.

      
- `ignore_out_of_context_barge_in` (Boolean; default value is `False`). 

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

#### Adding built-in condition functions

The following built-in condition functions have been added

-  `_confidence_is_low()` 

   入力の`aux_data`の`confidence`の値がコンフィギュレーションの`input_confidence_threshold`の値以下の場合にTrueを返します．

   Returns True if the value of `confidence` in the    input `aux_data` is less than or equal to the value of `input_confidence_threshold` in the configuration.

   
-  `_is_long_silence()`

    Returns `True` if the value of `long_silence` in the input's `aux_data` is `True`.

#### Ignoring the last incorrect input

入力の`aux_data`の`rewind`の値が`True`の場合，直前のレスポンスを行う前の状態から遷移を行います．
直前のレスポンスを行った際に実行したアクションによる対話文脈の変更も元に戻されます．

If the value of `rewind` in the input `aux_data` is `True`, a transition is made from the state before the last response.
Any changes to the dialog context due to actions taken during the previous response will also be undone.


音声認識の際に，ユーザ発話を間違って途中で分割してしまい，前半だけに対する応答を行ってしまった場合に用います．
This function is used when a user's speech is accidentally split in the middle during speech recognition and only the first half of the speech is responded to.

対話文脈は元に戻りますが，アクション関数の中でグローバル変数の値を変更していたり，外部データベースの内容を変更していた場合にはもとに戻らないことに注意してください．

Note that the interactive context is restored, but not if you have changed the value of a global variable in an action function or the contents of an external database.

