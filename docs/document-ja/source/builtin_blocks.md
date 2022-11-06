# 組み込みブロックの仕様


組み込みブロックとは，DialBBにあらかじめ含まれているブロックです．


## Utterance canonicalizer 

(`preprocess.utterance_canonicalizer.UtteranceCanonicalizer`)

ユーザ入力文の正規化を行います．

configurationの`language`要素が`ja`の場合は日本語，`en`の場合は英語用の正規化を行います．

- 入力
  - `input_text`: ユーザ発話文字列（文字列）
    - 例："ＣＵＰ Noodle 好き"

- 出力
  - `output_text`: 正規化後のユーザ発話（文字列）
    - 例："cupnoodle好き"

正規化は以下の処理を行います．

- 大文字→小文字
- 全角→半角の変換（カタカナを除く）
- スペースの連続を一つのスペースに変換（英語のみ）
- スペースの削除（日本語のみ）



## SNIPS understander 

(`understanding_with_snips.snips_understander.Understander`)  

[SNIPS_NLU](https://snips-nlu.readthedocs.io/en/latest/)を利用して，ユーザ発話タイプ（インテントとも呼びます）の決定とスロットの抽出を行います．

configurationの`language`要素が`ja`の場合は日本語，`en`の場合は英語の言語理解を行います．

本ブロックは，起動時にExcelで記述した言語理解用知識を読み込み，SNIPSの訓練データに変更し，SNIPSのモデルを構築します．

実行時はSNIPSのモデルを用いて言語理解を行います．

- 入力
  - `input_text`: 正規化後のユーザ発話（文字列）
    - 例："好きなのは醤油"
- 出力
  - `nlu_result`: 言語理解結果（辞書型）
    - 例：`{"type": "特定のラーメンが好き", "slots": {"favarite_ramen": "醤油ラーメン"}}}`
- 知識記述はExcelファイルで行います． block configurationのknowledge_fileにファイル名を指定します．
  ファイル名はconfigurationファイルからの相対パスで記述します．

(nlu_knowledge)=

### 言語理解知識

言語理解知識は，以下の４つのシートからなります．

| シート名   | 内容                                   |
| ---------- | -------------------------------------- |
| utterances | タイプ毎の発話例                       |
| slots      | スロットとエンティティの関係           |
| entities   | エンティティに関する情報               |
| dictionary | エンティティ毎の辞書エントリーと同義語 |

シート名はblock configurationで変更可能ですが，変更することはほとんどないと思いますので，詳細な説明は割愛します．

#### utterancesシート

各行は次のカラムからなります．

| カラム名  | 内容                                                         |
| --------- | ------------------------------------------------------------ |
| flag      | 利用するかどうかを決めるフラグ．Y: yes, T: testなどを書くことが多い．<br />どのフラグの行を利用するかはコンフィギュレーションに記述する．<br />サンプルアプリのコンフィギュレーションでは，すべての行を使う設定になっている． |
| type      | 発話のタイプ（インテント）                                   |
| utterance | 発話例．スロットを<br />`(豚骨ラーメン)[favorite_ramen]が好きです`<br />のように<br />`(<スロットに対応する言語表現>)[<スロット名>]`<br />で表現する．<br />スロットに対応する言語表現＝言語理解結果に表れる（すなわちmanagerに送られる）<br />スロット値ではないことに注意．<br />言語表現がdictionaryのsynonymsカラムにあるものの場合，<br />スロット値は，dictionaryシートのvalueカラムに書かれたものになる． |

#### slotsシート

各行は次のカラムからなります．

| カラム名 | 内容                                                         |
| -------- | ------------------------------------------------------------ |
| flag     | utterancesシートと同じ                                       |
| slot     | スロット名．utterancesシートの発話例で使うもの．言語理解結果でも用いる． |
| entity   | エンティティ名．スロットの値がどのようなタイプの名詞句なのかを表す．<br />異なるスロットが同じエンティティを持つ場合がある．例えば，<br />`(東京)[source_station]から(京都)[destination_station]までの特急券を買いたい`<br />のように，`source_station, destination_station`とも`station`エンティティを取る．<br />entityカラムの値は，SNIPSの[builtin entity](https://snips-nlu.readthedocs.io/en/latest/builtin_entities.html)でも良い．（例: `snips/city`） |

SNIPSのbuiltin entityを用いる場合，以下のようにしてインストールする必要があります．

```
$ snips-nlu download-entity snips/city ja
```

SNIPSのbuiltin entityを用いた場合の精度などの検証は不十分です．

#### entitiesシート

#### 各行は次のカラムからなります．

| カラム名                   | 内容                                                         |
| -------------------------- | ------------------------------------------------------------ |
| flag                       | utterancesシートと同じ                                       |
| entity                     | エンティティ名                                               |
| use synonyms               | [同義語を使うかどうか](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#entity-values-synonyms) (YesまたはNo) |
| automatically `extensible` | [辞書にない値でも認識するかどうか](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#auto-extensible) (YesまたはNo) |
| matching strictness        | [エンティティのマッチングの厳格さ](https://snips-nlu.readthedocs.io/en/latest/api.html) 0.0 - 1.0 |

#### dictionaryシート

各行は次のカラムからなります．

| カラム名 | 内容                                       |
| -------- | ------------------------------------------ |
| flag     | utterancesシートと同じ                     |
| entity   | エンティティ名                             |
| value    | 辞書エントリー名．言語理解結果にも含まれる |
| synonyms | 同義語を`,`, `，`,`，`で連結したもの       |

#### SNIPSの訓練データ

アプリを立ち上げると上記の知識はSNIPSの訓練データに変換され，モデルが作られます．

SNIPSの訓練データはアプリのディレクトリの`_training_data.json`です．このファイルを見ることで，うまく変換されているかどうかを確認できます．

(stn_manager)=
## STN manager

状態遷移ネットワーク(State-Transition Network)を用いて対話管理を行います．

- 入力
  - `sentence`: 正規化後のユーザ発話（文字列）
  - `nlu_result`:言語理解結果（辞書型）
  - `user_id`:ユーザID（文字列）
  - `aux_data`補助データ（辞書型）
- 出力
  - `output_text`: システム発話（文字列）
    - 例："醤油ラーメン好きなんですね"
  - `final`: 対話終了かどうかのフラグ（ブール値）
  - `aux_data`補助データ（辞書型）遷移した状態のIDを含めて返す
    - 例：`{"state": "特定のラーメンが好き"}`
- 知識記述はExcelファイルで行います． block configurationのknowledge_fileにファイル名を指定します．
  ファイル名はconfigurationファイルからの相対パスで記述します．

(scenario)=
### 対話管理の知識記述

対話管理知識（シナリオ）は，Excelファイルのscenarioシートです．

各行は次のカラムからなります．

| カラム名               | 内容                                                         |
| ---------------------- | ------------------------------------------------------------ |
| flag                   | utteranceシートと同じ                                        |
| state                  | stateのID                                                    |
| system  utterance      | stateの状態で生成されるシステム発話の候補．システム発話文字列に含まれる{<変数>}は，<br />対話中にその変数に代入された値で置き換えられる．stateが同じ行は複数あり得るが，<br />同じstateの行のsystem utteranceすべてが発話の候補となり，ランダムに生成される． |
| user utterance example | ユーザ発話の例．対話の流れを理解するために書くだけで，システムでは用いられない． |
| user utterance type    | ユーザ発話を言語理解した結果得られるユーザ発話のタイプ．遷移の条件となる． |
| conditions             | 条件（の並び）．遷移の条件を表す関数呼び出し．複数あっても良い．<br />複数ある場合は，`;`で連結する．<br />各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしている．<br />引数は0個でも良い． |
| actions                | アクション（の並び）．遷移した際に実行する関数呼び出し．<br />複数あっても良い．複数ある場合は，`;`で連結する．<br />各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしている．<br />引数は0個でも良い． |
| next state             | 遷移先のstate                                                |

基本的に1行が一つの遷移を表します．各遷移のuser utterance typeが空かもしくは言語理解結果と一致し，conditionsが空か全部満たされた場合，遷移の条件を満たし，next stateに遷移します．その際，actionsを実行します．

### 特別なstate

以下のstate IDはあらかじめ定義されています．

| state ID | 説明                                                         |
| -------- | ------------------------------------------------------------ |
| #initial | 初期状態．対話はこの状態から始まる．                         |
| #error   | 内部エラーが起きたときこの状態に移動する．システム発話を生成して終了する． |


また，`#final_say_bye` のように，`#final`ではじまるstate IDは最終状態を表します．
最終状態ではシステム発話を生成して対話を終了します．


### 条件とアクション

STN Managerは，対話のセッションごとに文脈情報を保持しています．文脈情報は変数とその値の組の集合（pythonの辞書型データ）で，値はどのようなデータ構造でも構いません．

条件やアクションの関数は文脈情報にアクセスします．

#### 関数の引数

conditionやactionで用いる関数の引数には次のタイプがあります．

| 引数のタイプ | 形式             | 説明                                                         |
| ------------ | ---------------- | ------------------------------------------------------------ |
| 特殊変数     | #で始まる文字列  | 言語理解をもとにセットされる変数の値<br />#<スロット名>: 直前のユーザ発話のスロット値．スロット値が空の場合は空文字列になる．<br />#<補助データのキー>: 入力のaux_dataの中のこのキーの値．例えば#emotionの場合、aux_data['emotion']の値。このキーがない場合は、空文字列になる。<br />#sentence: 直前のユーザ発話（正規化したもの）<br />#user_id: ユーザID（文字列） |
| 変数         | *で始まる文字列  | 文脈情報における変数の値<br />*<変数名>の形．<br />変数の値は文字列でなくてはならない．文脈情報にその変数がない場合は空文字列になる． |
| 変数参照     | &で始まる文字列  | &<変数名>: 文脈情報での変数の名前．関数定義内で文脈情報の変数名を利用するときに用いる． |
| 定数         | ""で囲んだ文字列 | 文字列                                                       |

### 関数定義

conditionやactionで用いる関数は，DialBB組み込みのものと，開発者が定義するものがあります．conditionで使う関数はbool値を返し，actionで使う関数は何も返しません．

#### 組み込み関数

組み込み関数には以下があります．

| 関数                 | condition or action | 説明                                                         | 使用例                                                       |
| -------------------- | ------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| _eq(x, y)            | condition           | xとyが同じならTrueを返す                                     | \_eq(*a, "b"): 変数aの値が"b"ならTrueを返す．<br />_eq(#food, "ラーメン"): #foodスロットが"ラーメン"ならTrueを返す |
| _ne(x, y)            | condition           | xとyが同じでなければTrueを返す                               | \_ne(*a, *b): 変数aの値と変数bの値が異なればTrueを返す<br />_ne(#food, "ラーメン"): #foodスロットが"ラーメン"ならFalseを返す |
| _contains(x, y)      | condition           | xが文字列としてyを含む場合Trueを返す                         | _contains(#sentence, "はい") : ユーザ発話が「はい」を含めばTrueを返す |
| _not_contains(x, y)  | condition           | xが文字列としてyを含まない場合Trueを返す                     | _not_contains(#sentence, "はい") : ユーザ発話が「はい」を含めばTrueを返す |
| _member_of(x, y)        | condition           | 文字列yを':'で分割してできたリストに文字列xが含まれていればTrueを返す | _member_of(#food, "ラーメン:チャーハン:餃子")                   |
| _not_member_of(x, y) | condition           | 文字列yを':'で分割してできたリストに文字列xが含まれていなければTrueを返す | _not_member_of(*favorite_food, "ラーメン:チャーハン:餃子")          |
| _set(x, y)           | action              | 変数xにyをセットする                                         | \_set(&a, b): bの値をaにセットする．<br />例：\_set(&a, "hello"): aに"hello"をセットする． |

#### 開発者による関数定義

開発者が関数定義を行うときには，アプリケーションディレクトリのscenario_functions.pyを編集します．

```python
def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None:
    location:str = ramen_map.get(ramen, "日本")
    context[variable] = location
```

上記のように，シナリオで使われている引数にプラスして，文脈情報を受け取るdict型の変数を必ず加える必要があります．

シナリオで使われている引数はすべて文字列でなくてはなりません．

引数には，特殊変数・変数の場合，その値が渡されます．

また，変数参照の場合は'&'を除いた変数名が，定数の場合は，""の中の文字列が渡されます．

contextは対話の最初に以下のキーと値のペアがセットされています．

| キー          | 値                                                           |
| ------------- | ------------------------------------------------------------ |
| _state        | state id                                                     |
| _config       | configファイルを読み込んでできたdict型のデータ               |
| _block_config | configファイルのうち対話管理ブロックの設定部分（dict型のデータ） |





