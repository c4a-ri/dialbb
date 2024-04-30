# 組み込みブロッククラスの仕様

組み込みブロッククラスとは，DialBBにあらかじめ含まれているブロッククラスです．

ver0.3で正規化ブロッククラスが変更になりました．また，新たに単語分割のブロッククラスが導入されました．
それに伴い，Snips言語理解の入力も変更になっています．

(japanese_canonicalizer)=

## Japanese canonicalizer （日本語文字列正規化ブロック）

(`dialbb.builtin_blocks.preprocess.japanese_canonicalizer.JapaneseCanonicalizer`)

入力文字列の正規化を行います．

### 入出力

- 入力
  - `input_text`: 入力文字列（文字列）
    - 例："ＣＵＰ Noodle 好き"

- 出力
  - `output_text`: 正規化後の文字列（文字列）
    - 例："cupnoodle好き"

### 処理内容

入力文字列に対して以下の処理を行います．

- 前後のスペースの削除
- 英大文字→英小文字
- 改行の削除
- 全角→半角の変換（カタカナを除く）
- スペースの削除
- Unicode正規化（NFKC）

(simple_canonicalizer)=

## Simple canonicalizer （単純文字列正規化ブロック）

(`dialbb.builtin_blocks.preprocess.simple_canonicalizer.SimpleCanonicalizer`)

ユーザ入力文の正規化を行います．主に英語が対象です．

### 入出力

- 入力
  - `input_text`: 入力文字列（文字列）
    - 例：`" I  like ramen"`

- 出力
  - `output_text`: 正規化後の文字列（文字列）
    - 例：`"i like ramen"`

### 処理内容

入力文字列に対して以下の処理を行います．

- 前後のスペースの削除
- 英大文字→英小文字
- 改行の削除
- スペースの連続を一つのスペースに変換


(sudachi_tokenizer)=

## Sudachi tokenizer （Sudachiベースの日本語単語分割ブロック）

(`dialbb.builtin_blocks.tokenization.sudachi_tokenizer.SudachiTokenizer`)

[Sudachi](https://github.com/WorksApplications/Sudachi)を用いて入力文字列を単語に分割します．

### 入出力

- 入力
  - `input_text`: 入力文字列（文字列）
    - 例："私はラーメンが食べたい"

- 出力
  - `tokens`: トークンのリスト（文字列のリスト）
    - 例：`['私','は','ラーメン','が','食べ','たい']`
  - `tokens_with_indices`: トークン情報のリスト（`dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`クラスのオブジェクトのリスト）．トークン情報には，トークンに加えてそのトークンが元の文字列の何文字目から何文字目までなのかの情報も含まれています．

### 処理内容

Sudachiの`SplitMode.C`を用いて単語分割します．

ブロックコンフィギュレーションの`sudachi_normalization`の値が`True`の時，Sudachi正規化を行います．
デフォルト値は`False`です．

(whitespace_tokenizer)=

## Whitespace tokenizer （空白ベースの単語分割ブロック）

(`dialbb.builtin_blocks.tokenization.whitespace_tokenizer.WhitespaceTokenizer`)

入力を空白で区切って単語に分割します．主に英語が対象です．

### 入出力

- 入力
  - `input_text`: 入力文字列（文字列）
    - 例：`"i like ramen"`

- 出力
  - `tokens`: トークンのリスト（文字列のリスト）
    - 例：`['i', 'like', 'ramen']`
  - `tokens_with_indices`: トークン情報のリスト（`dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`クラスのオブジェクトのリスト）．トークン情報には，トークンに加えてそのトークンの開始位置が元の文字列の何文字目から何文字目までなのかの情報も含まれています．

### 処理内容

単純正規化ブロックで正規化された入力を空白で区切って単語に分割します．


(snips_understander)=

## Snips understander （Snipsを用いた言語理解ブロック）

(`dialbb.builtin_blocks.understanding_with_snips.snips_understander.Understander`)  

[Snips_NLU](https://snips-nlu.readthedocs.io/en/latest/)を利用して，ユーザ発話タイプ（インテントとも呼びます）の決定とスロットの抽出を行います．

コンフィギュレーションの`language`要素が`ja`の場合は日本語，`en`の場合は英語の言語理解を行います．

本ブロックは，起動時にExcelで記述した言語理解用知識を読み込み，Snipsの訓練データに変換し，Snipsのモデルを構築します．

実行時は，構築されたSnipsのモデルを用いて言語理解を行います．

### 入出力

- 入力

  - `tokens`: トークンのリスト（文字列のリスト）
    - 例：['好き','な','の','は','醤油']

- 出力

  - `nlu_result`: 言語理解結果（辞書型または辞書型のリスト）

    - 後述のブロックコンフィギュレーションのパラメータ`num_candidates`が`1`の場合，言語理解結果は辞書型で以下のような形式です．

      ```json
       {
       "type": <ユーザ発話タイプ（インテント）>, 
         "slots": {
          <スロット名>: <スロット値>, 
        ..., 
        <スロット名>: <スロット値>
       }
      }
      ```

      以下が例です．

      ```json
       {
       "type": "特定のラーメンが好き", 
       "slots": {
          "favorite_ramen": "醤油ラーメン"
       }
       }
      ```

    - `num_candidates`が2以上の場合，複数の理解結果候補のリストになります．

      ```json
       [
       {
         "type": <ユーザ発話タイプ（インテント）>, 
           "slots": {
           <スロット名>: <スロット値>, 
      	 ..., 
      	 <スロット名>: <スロット値>
       }
      },
        {
        "type": <ユーザ発話タイプ（インテント）>, 
          "slots": {
        <スロット名>: <スロット値>, 
        ..., 
        <スロット名>: <スロット値>
        }
      },
        ....
      ]
      ```

### ブロックコンフィギュレーションのパラメータ

- `knowledge_file`（文字列）

  知識を記述したExcelファイルを指定します．コンフィギュレーションファイルのあるディレクトリからの相対パスで記述します．

- `function_definitions`（文字列）

  辞書関数（{ref}`dictionary_function`を参照）を定義したモジュールの名前です．複数ある場合は`':'`でつなぎます．モジュール検索パスにある必要があります．（コンフィギュレーションファイルのあるディレクトリはモジュール検索パスに入っています．）

- `flags_to_use`（文字列のリスト）

  各シートの`flag`カラムにこの値のうちのどれかが書かれていた場合に読み込みます．このパラメータがセットされていない場合はすべての行が読み込まれます．

- `canonicalizer` 

  言語理解知識をSnipsの訓練データに変換する際に行う正規化の情報を指定します．

  - `class` （文字列）

    正規化のブロックのクラスを指定します．基本的にアプリケーションで用いる正規化のブロックと同じものを指定します．

- `tokenizer` 

  言語理解知識をSnipsの訓練データに変換する際に行う単語分割の情報を指定します．

  - `class` （文字列）

    単語分割のブロックのクラスを指定します．基本的にアプリケーションで用いる単語分割のブロックと同じものを指定します．

  - `sudachi_normalization`（ブール値．デフォルト値`False`）

    単語分割にSudachi Tokenizerを用いる場合，この値が`True`の時には，Sudachi正規化を行います．

- `num_candidates`（整数．デフォルト値`1`）

  言語理解結果の最大数（n-bestのn）を指定します．

- `knowledge_google_sheet` (ハッシュ)

  - Excelの代わりにGoogle Sheetを用いる場合の情報を記述します．（Google Sheetを利用する際の設定は[こはたさんの記事](https://note.com/kohaku935/n/nc13bcd11632d)が参考になりますが，Google Cloud Platformの設定画面のUIがこの記事とは多少変わっています．）


    - `sheet_id` （文字列）
    
      Google SheetのIDです．
    
    - `key_file`（文字列）
    
      Goole Sheet APIにアクセスするためのキーファイルをコンフィギュレーションファイルのディレクトリからの相対パスで指定します．


(nlu_knowledge)=

### 言語理解知識

言語理解知識は，以下の４つのシートからなります．

| シート名   | 内容                                   |
| ---------- | -------------------------------------- |
| utterances | タイプ毎の発話例                       |
| slots      | スロットとエンティティの関係           |
| entities   | エンティティに関する情報               |
| dictionary | エンティティ毎の辞書エントリーと同義語 |

シート名はブロックコンフィギュレーションで変更可能ですが，変更することはほとんどないと思いますので，詳細な説明は割愛します．

（注）各シートのカラム名がver0.2.0で変更されました．

#### utterancesシート

各行は次のカラムからなります．

- `flag`      

  利用するかどうかを決めるフラグ．`Y` (yes), `T` (test)などを書くことが多いです．どのフラグの行を利用するかはコンフィギュレーションに記述します．サンプルアプリのコンフィギュレーションでは，すべての行を使う設定になっています． 

- `type`     

  発話のタイプ（インテント）                         

- `utterance` 

  発話例．スロットを`(豚骨ラーメン)[favorite_ramen]が好きです`のように`(<スロットに対応する言語表現>)[<スロット名>]`で表現します．スロットに対応する言語表現＝言語理解結果に表れる（すなわちmanagerに送られる）スロット値ではないことに注意して下さい．言語表現が`dictionary`シートの`synonyms`カラムにあるものの場合，スロット値は，`dictionary`シートの`entity`カラムに書かれたものになります． 

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
  またentity classカラムの値は，Snipsの[builtin entity](https://snips-nlu.readthedocs.io/en/latest/builtin_entities.html)でも構いません．（例: `snips/city`）

  Snipsのbuiltin entityを用いる場合，以下のようにしてインストールする必要があります．

  ```sh
  $ snips-nlu download-entity snips/city ja
  ```

  Snipsのbuiltin entityを用いた場合の精度などの検証は不十分です．

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

  同義語を`','`または `'，'`または`'，'`で連結したもの

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

#### Snipsの訓練データ

アプリを立ち上げると上記の知識はSnipsの訓練データに変換され，モデルが作られます．

Snipsの訓練データはアプリのディレクトリの`_training_data.json`です．このファイルを見ることで，うまく変換されているかどうかを確認できます．

(chatgpt_understander)=

## ChatGPT Understander （ChatGPTを用いた言語理解ブロック）

(`dialbb.builtin_blocks.understanding_with_chatgpt.chatgpt_understander.Understander`）

OpenAI社のChatGPTを用いて，ユーザ発話タイプ（インテントとも呼びます）の決定とスロットの抽出を行います．

コンフィギュレーションの`language`要素が`ja`の場合は日本語，`en`の場合は英語の言語理解を行います．

本ブロックは，起動時にExcelで記述した言語理解用知識を読み込み，プロンプトのユーザ発話タイプのリスト，スロットのリスト，Few shot exampleに変換します．

実行時は，プロンプトに入力発話を付加してChatGPTに言語理解を行わせます．

### 入出力

- 入力

  - `input_text`: 入力文字列

   入力文字列は正規化されていると仮定します．

     例："好きなのは醤油"

- 出力

  - `nlu_result`: 言語理解結果（辞書型）


    以下の形式
    
    ```json
    {
      "type": <ユーザ発話タイプ（インテント）>, 
      "slots": {
         <スロット名>: <スロット値>, 
         ..., 
         <スロット名>: <スロット値>
        }
    }
    ```
    
    以下が例です．
    
    ```json
    {
      "type": "特定のラーメンが好き", 
      "slots": {
         "favorite_ramen": "醤油ラーメン"
      }
    }
    ```

### ブロックコンフィギュレーションのパラメータ

- `knowledge_file`（文字列）

  知識を記述したExcelファイルを指定します．コンフィギュレーションファイルのあるディレクトリからの相対パスで記述します．

- `flags_to_use`（文字列のリスト）

  各シートの`flag`カラムにこの値のうちのどれかが書かれていた場合に読み込みます．このパラメータがセットされていない場合はすべての行が読み込まれます．

- `canonicalizer` 

  辞書記述を正規化する際に使うプログラムを指定します．

  - `class` （文字列）

    正規化のブロックのクラスを指定します．基本的にアプリケーションで用いる正規化のブロックと同じものを指定します．

- `knowledge_google_sheet` (ハッシュ)

  - Excelの代わりにGoogle Sheetを用いる場合の情報を記述します．（Google Sheetを利用する際の設定は[こはたさんの記事](https://note.com/kohaku935/n/nc13bcd11632d)が参考になりますが，Google Cloud Platformの設定画面のUIがこの記事とは多少変わっています．）

    - `sheet_id` （文字列）

      Google SheetのIDです．

    - `key_file`（文字列）

      Goole Sheet APIにアクセスするためのキーファイルをコンフィギュレーションファイルのディレクトリからの相対パスで指定します．

- `gpt_model` (文字列．デフォルト値は`gpt-3.5-turbo`）

  ChatGPTのモデルを指定します．`gpt-4-turbo`などが指定できます．`gpt-4`は指定できません．

- `prompt_template`

  プロンプトテンプレートを書いたファイルをコンフィギュレーションファイルのディレクトリからの相対パスで指定します．

  これが指定されていない場合は，`dialbb.builtin_blocks.understanding_with_chatgpt.prompt_templates_ja .PROMPT_TEMPLATE_JA` （日本語）または，`dialbb.builtin_blocks.understanding_with_chatgpt.prompt_templates_en .PROMPT_TEMPLATE_EN` （英語）が使われます．

  プロンプトテンプレートは，言語理解をChatGPTに行わせるプロンプトのテンプレートで，`@`で始まる以下の変数を含みます．

  - `@types` 発話タイプの種類を列挙したものです．
  - `@slot_definitions` スロットの種類を列挙したものです．
  - `@examples` 発話例と，タイプ，スロットの正解を書いたいわゆるfew shot exampleです．
  - `@input` 入力発話です．

  これらの変数には，実行時に値が代入されます．


(chatgpt_nlu_knowledge)=

### 言語理解知識

言語理解知識は，以下の2つのシートからなります．

| シート名   | 内容                                             |
| ---------- | ------------------------------------------------ |
| utterances | タイプ毎の発話例                                 |
| slots      | スロットとエンティティの関係および同義語のリスト |

シート名はブロックコンフィギュレーションで変更可能ですが，変更することはほとんどないと思いますので，詳細な説明は割愛します．

#### utterancesシート

各行は次のカラムからなります．

- `flag`      

  利用するかどうかを決めるフラグ．`Y` (yes), `T` (test)などを書くことが多いです．どのフラグの行を利用するかはコンフィギュレーションに記述します．サンプルアプリのコンフィギュレーションでは，すべての行を使う設定になっています． 

- `type`   

  発話のタイプ（インテント）                         

- `utterance` 

  発話例．

- `slots` 

  発話に含まれるスロット．スロットを以下の形で記述します．

  ```
  <スロット名>=<スロット値>, <スロット名>=<スロット値>, ... <スロット名>=<スロット値> 
  ```

  以下が例です．

  ```
  地方=札幌, 好きなラーメン=味噌ラーメン
  ```

  utterancesシートのみならずこのブロックで使うシートにこれ以外のカラムがあっても構いません．

#### slotsシート

各行は次のカラムからなります．

- `flag`

  utterancesシートと同じ

- `slot name` 

  スロット名．utterancesシートの発話例で使うもの．言語理解結果でも用います．

- `entity`

  辞書エントリー名．言語理解結果に含まれます．

- `synonyms`

  同義語を`','`で連結したものです．


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

  Snips Understanderと同じです．

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

  `state`の状態で生成されるシステム発話の候補．

  システム発話文字列に含まれる`{<変数>}`または{<関数呼び出し>}`は，対話中にその変数に代入された値や関数呼び出しの結果で置き換えられます．これについては，以下の「{ref}`realization_in_system_utterance`」で詳しく説明します．


  `state`が同じ行は複数あり得ますが，同じ`state`の行の`system utterance`すべてが発話の候補となり，ランダムに生成されます．

- `user utterance example`

  ユーザ発話の例．対話の流れを理解するために書くだけで，システムでは用いられません．

- `user utterance type`

  ユーザ発話を言語理解した結果得られるユーザ発話のタイプ．遷移の条件となります．

- `conditions`

  条件（の並び）．遷移の条件を表す関数呼び出し．複数あっても構いません．複数ある場合は，`';'`で連結します．各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしています．引数は0個でも構いません．各条件で使える引数については，「{ref}`arguments`」を参照してください．

- `actions`

  アクション（の並び）．遷移した際に実行する関数呼び出し．複数あっても構いません．複数ある場合は，`;`で連結します．各条件は`<関数名>(<引数1>, <引数2>, ..., <引数n>)`の形をしています．引数は0個でも構いません．各条件で使える引数については，{ref}`arguments`を参照してください．

- `next state`

  遷移先の状態名

（メモとして利用するために）シートにこれ以外のカラムがあっても構いません．

各行が表す遷移の`user utterance type`が空かもしくは言語理解結果と一致し，`conditions`が空か全部満たされた場合，遷移の条件を満たし，`next state`の状態に遷移します．その際，`actions`に書いてあるアクションが実行されます．

`state`カラムが同じ行（遷移元の状態が同じ遷移）は，**上に書いてあるものから順に**遷移の条件を満たしているかどうかをチェックします．

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

| キー                       | 値                                                           |
| -------------------------- | ------------------------------------------------------------ |
| _current_state_name        | 遷移前状態の名前（文字列）                                   |
| _config                    | configファイルを読み込んでできた辞書型のデータ               |
| _block_config              | configファイルのうち対話管理ブロックの設定部分（辞書型のデータ） |
| _aux_data                  | メインプロセスから受け取ったaux_data（辞書型のデータ）       |
| _previous_system_utterance | 直前のシステム発話（文字列）                                 |
| _dialogue_history          | 対話履歴（リスト）                                           |


対話履歴は，以下の形です．

```python
[
  {
    "speaker": "user",
    "utterance": <正規化後のユーザ発話(文字列)>
  },
  {
    "speaker": "system",
    "utterance": <システム発話>
  },
  {
    "speaker": "user",
    "utterance": <正規化後のユーザ発話(文字列)>
  },
  {
    "speaker": "system",
    "utterance": <システム発話>
  },
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

    入力の`aux_data`の中のこのキーの値．例えば`#emotion`の場合，`aux_data['emotion']`の値．このキーがない場合は，空文字列になります．

  - `#sentence`

    直前のユーザ発話（正規化したもの）

  - `#user_id`

    ユーザID（文字列）

- 変数（`*`で始まる文字列）

  文脈情報における変数の値です．`*<変数名>`の形．変数の値は文字列でないといけません．文脈情報にその変数がない場合は空文字列になります．

- 変数参照（&で始まる文字列）

  `&<文脈情報での変数の名前>` の形で，関数定義内で文脈情報の変数名を利用するときに用います．

- 定数（`""`で囲んだ文字列）

  文字列そのままを意味します．


(realization_in_system_utterance)=

### システム発話中の変数や関数呼び出しの扱い

システム発話中の`{`と`}`に囲まれた部分の変数や関数呼び出しは，その変数の値や，関数呼び出しの返り値で置き換えられます．

変数は`#`で始まるものは上記の特殊変数です．それ以外のものは通常の変数で，文脈情報にあるはずのものです．それらの変数が存在しない場合は，置換されず変数名がそのまま使われます．

関数呼び出しの場合，関数は条件やアクションで用いる関数と同じように上記の引数を取ることができます．返り値は文字列でないといけません．


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

  - `_not_member_of(x, y)`

  - `_num_turns_exceeds(n)`

    文字列`n`が表す整数よりもターン数（ユーザの発話回数）が多いとき，`True`を返します．

    例：`_num_turns_exceeds("10")`

  - `_check_with_llm(task)`

    大規模言語モデル（現在はOpenAIのChatGPTのみ）を用いて判定をします．後述します．


- アクションで用いる関数

  - `_set(x, y)`

    変数`x`に`y`をセットします．

    例：`_set(&a, b)`: `b`の値を`a`にセットします．
    `_set(&a, "hello")`： `a`に`"hello"`をセットします．

  - `_set(x, y)`

    変数`x`に`y`をセットします．

    例：`_set(&a, b)`: `b`の値を`a`にセットします．
    `_set(&a, "hello")`： `a`に`"hello"`をセットします．


- システム発話内で用いる関数

  - `_generate_with_llm(task)`

    大規模言語モデル（現在はOpenAIのChatGPTのみ）を用いて文字列を生成します．後述します．

#### 大規模言語モデルを用いた組み込み関数

`_check_with_llm(task)`および`_generate_with_llm(task)`は，大規模言語モデル（現在はOpenAIのChatGPTのみ）と，対話履歴を用いて，条件の判定および文字列の生成を行います．以下が例です．

- 条件判定の例

  ```python
  _check_with_llm("ユーザが理由を言ったかどうか判断してください．")
  ```

- 文字列生成の例

  ```python
  _generate_with_llm("それまでの会話につづけて，対話を終わらせる発話を50文字以内で生成してください")
  ```

これらの関数を使うためには，以下の設定が必要です．

- 環境変数`OPENAI_API_KEY`にOpenAIのAPIキーをセットする

  OpenAIのAPIキーの取得の仕方はWebサイトなどで調べてください．

- ブロックコンフィギュレーションの`chatgpt`要素に以下の要素を加える

  - `gpt_model` （文字列） 

    GPTのモデル名です．`gpt-4-turbo`, `gpt-3.5-turbo`等を指定できます．デフォルト値は`gpt-3.5-turbo`です．`gpt-4`は指定できません．

  - `temperature` (float)

    GPTの温度パラメータです．デフォルト値は`0.7`です．

  - `situation` （文字列のリスト）

    GPTのプロンプトに書く状況を列挙したものです．

    この要素がない場合，状況は指定されません．

  - `persona` （文字列のリスト）

    GPTのプロンプトに書くシステムのペルソナを列挙したものです．

    この要素がない場合，ペルソナは指定されません．

  例：

  ```yaml
  chatgpt:
    gpt_model: gpt-4-turbo
    temperature: 0.7
    situation:
      - あなたは対話システムで，ユーザと食べ物に関して雑談をしています．
      - ユーザとは初対面です
      - ユーザとは同年代です
      - ユーザとは親しい感じで話します
    persona:
      - 名前は由衣
      - 28歳
      - 女性
      - ラーメン全般が好き
      - お酒は飲まない
      - IT会社のwebデザイナー
      - 独身
      - 非常にフレンドリーに話す
      - 外交的で陽気
  ```

#### 組み込み関数の簡略記法

組み込み関数の記述を簡単にするために以下の簡略記法（Syntax Sugar)が用意されています．

- `<変数名>==<値>`

  `_eq(<変数名>, <値>)`の意味です．

  例：

  ```
  #好きなラーメン=="豚骨ラーメン"
  ```

- `<変数名>!=<値>`

  `_ne(<変数名>, <値>)`の意味です．

  例：

  ```
  #NE_Person!=""
  ```

- `<変数名>=<値>`

  `_set(&<変数名>, <値>)`の意味です．

  例：

  ```
  user_name=#NE_Person
  ```

- `$<タスク文字列>`

  条件として使われた時は，`_check_with_llm(<タスク文字列>)`の意味で，システム発話中に`{}`で囲まれて文字列生成として使われた時は，`_generate_with_llm(<タスク文字列>)`の意味です．

  条件の例：

  ```
  $"ユーザが理由を言ったかどうか判断してください．"
  ```

​  文字列生成を含むシステム発話の例：

  ```
  わかりました．{$"それまでの会話につづけて，対話を終わらせる発話を50文字以内で生成してください．"}今日はお時間ありがとうございました．
  ```


#### 開発者による関数定義

開発者が関数定義を行うときには，コンフィギュレーションファイルのブロックコンフィギュレーションの`function_definition`で指定されているモジュールのファイル（Snips+STN Managerアプリでは`scenario_functions.py`）を編集します．

```python
def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None:
    location:str = ramen_map.get(ramen, "日本")
    context[variable] = location
```

上記のように，シナリオで使われている引数にプラスして，文脈情報を受け取る辞書型の変数を必ず加える必要があります．

シナリオで使われている引数はすべて文字列でなくてはなりません．

引数には，特殊変数・変数の場合，その値が渡されます．

また，変数参照の場合は`'&'`を除いた変数名が，定数の場合は，`""`の中の文字列が渡されます．


### 連続遷移

システム発話（の1番目）が`$skip`である状態に遷移した場合，システム応答を返さず，即座に次の遷移を行います．これは，最初の遷移のアクションの結果に応じて二つ目の遷移を選択するような場合に用います．

### 言語理解結果候補が複数ある場合の処理

入力の`nlu_result`がリスト型のデータで，複数の言語理解結果候補を含んでいる場合，処理は次のようになります．

リストの先頭から順に，言語理解結果候補の`type`の値が，現在の状態から可能な遷移のうちのどれかの`user utterance type`の値に等しいかどうかを調べ，等しい遷移があれば，その言語理解結果候補を用います．

どの言語理解結果候補も上記の条件に合わない場合，リストの先頭の言語理解結果候補を用います．

### リアクション

アクション関数の中で，文脈情報の`_reaction`に文字列をセットすると，状態遷移後のシステム発話の先頭に，その文字列を付加します．

例えば，`_set(&_reaction, "そうですね")`というアクション関数を実行した後に遷移した状態のシステム発話が`"ところで今日はいい天気ですね"`であれば，`"そうですね ところで今日はいい天気ですね"`という発話をシステム発話として返します．

### Subdialogue

遷移先の状態名が`#gosub:<状態名1>:<状態名2>`の形の場合，`<状態名1>`の状態に遷移して，そこから始まるsubdialogueを実行します．そして，その後の対話で，遷移先が`:exit`になったら，`<状態名2>`の状態に移ります．

例えば，遷移先の状態名が`#gosub:request_confirmation:confirmed`の形の場合，`request_confirmatin`から始まるsubdialogueを実行し，遷移先が`:exit`になったら，`confirmed`に戻ります．

subdialogueの中でsubdialogueに遷移することも可能です．


### 音声入力を扱うための仕組み

ver. 0.4.0で，音声認識結果を入力として扱うときに生じる問題に対処するため，以下の変更が行われました．

#### ブロックコンフィギュレーションパラメータの追加

- `input_confidence_threshold` （float．デフォルト値`0.0`）

  入力が音声認識結果の時，その確信度がこの値未満の場合に，確信度が低いとみなします．入力の確信度は，`aux_data`の`confidence`の値です．`aux_data`に`confidence`キーがないときは，確信度が高いとみなします．確信度が低い場合は，以下に述べるパラメータの値に応じて処理が変わります．

- `confirmation_request`（オブジェクト）

  これは以下の形で指定します．

  ```yaml
  confirmation_request:
    function_to_generate_utterance: <関数名（文字列）>
    acknowledgement_utterance_type: <肯定のユーザ発話タイプ名（文字列）>
    denial_utterance_type: <否定のユーザ発話タイプ名（文字列）>
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

  `action`要素を必ず持ちます．`action` 要素の値は文字列で`"repeat"`か`"transition"`です．`action` 要素の値が`transition`の場合，`destination` 要素が必須です．その値は状態名（文字列）です．

   入力の`aux_data`が`long_silence`キーを持ちその値が`True`の場合で，かつ，デフォルト遷移以外の遷移の条件を満たさなかった場合，このパラメータに応じて以下のように動作します．

    - このパラメータが指定されていない場合，通常の状態遷移を行います．

    - `action`の値が`"repeat"`の場合，状態遷移を行わず直前のシステム発話を繰り返します．

    - `action`の値が`transition`の場合，`destination`で指定されている状態に遷移します．

#### 組み込み条件関数の追加

以下の組み込み条件関数が追加されています．

- `_confidence_is_low()` 

  入力の`aux_data`の`confidence`の値がコンフィギュレーションの`input_confidence_threshold`の値以下の場合にTrueを返します．

- `_is_long_silence()`

  入力の`aux_data`の`long_silence`の値が`True`の場合に`True`を返します．

#### 直前の誤った入力を無視する

入力の`aux_data`の`rewind`の値が`True`の場合，直前のレスポンスを行う前の状態から遷移を行います．
直前のレスポンスを行った際に実行したアクションによる文脈情報の変更も元に戻されます．

音声認識の際に，ユーザ発話を間違って途中で分割してしまい，前半だけに対する応答を行ってしまった場合に用います．

文脈情報は元に戻りますが，アクション関数の中でグローバル変数の値を変更していたり，外部データベースの内容を変更していた場合にはもとに戻らないことに注意してください．



(chatgpt_dialogue)=

## ChatGPT Dialogue （ChatGPTベースの対話ブロック）

(ver0.6で追加，ver0.7で大幅に変更）

(`dialbb.builtin_blocks.chatgpt.chatgpt.ChatGPT`)

OpenAI社のChatGPTを用いて対話を行います．


### 入出力

- 入力
  - `user_utterance`: 入力文字列（文字列）
  - `aux_data`: 補助データ（辞書型）
  - `user_id`: 補助データ（辞書型）

- 出力
  - `system_utterance`: 入力文字列（文字列）
  - `aux_data`: 補助データ（辞書型）
  - `final`: 対話終了かどうかのフラグ（ブール値）


入力の`aux_data`, `user_id`利用せず，出力の`aux_data`は入力の`aux_data`と同じもので，`final`は常に`False`です．

これらのブロックを使う時には，環境変数`OPENAI_API_KEY`にOpenAIのライセンスキーを設定する必要があります．

### ブロックコンフィギュレーションのパラメータ

- `first_system_utterance` （文字列，デフォルト値は`""`）

  対話の最初のシステム発話です．

- `user_name` （文字列，デフォルト値は`"User"`）

  ChatGPTのプロンプトに使う文字列です．以下で説明します．

- `system_name` （文字列，デフォルト値は`"System"`）

  ChatGPTのプロンプトに使う文字列です．以下で説明します．

- `prompt_template` （文字列）

  ChatGPTのプロンプトのテンプレートを記述したファイル名です．アプリケーションディレクトリからの相対で記述します．

  プロンプトテンプレートは，システム発話の生成をChatGPTに行わせるプロンプトのテンプレートで，`@`で始まる以下の変数を含みます．

  - `@dialogue_history` 対話の履歴です．実行時に以下のような形の値が代入されます．

    ```
    <ブロックコンフィギュレーションのsystem_nameの値>: <システム発話>
    <ブロックコンフィギュレーションのuser_nameの値>: <ユーザ発話>
    <ブロックコンフィギュレーションのsystem_nameの値>: <システム発話>
    <ブロックコンフィギュレーションのuser_nameの値>: <ユーザ発話>
    ...
    <ブロックコンフィギュレーションのsystem_nameの値>: <システム発話>
    <ブロックコンフィギュレーションのuser_nameの値>: <ユーザ発話>
    ```

- `gpt_model` （文字列，デフォルト値は`gpt-3.5-turbo`）

  Open AI GPTのモデルです．`gpt-4`, `gpt-4-turbo`などが指定できます．

### 処理内容

- 対話の最初はブロックコンフィギュレーションの`first_system_utterance`の値をシステム発話として返します．

- 2回目以降のターンでは，プロンプトテンプレートの`@dialogue_history`に対話履歴を代入したものを与えてChatGPTに発話を生成させ，返ってきた文字列をシステム発話として返します．

(spacy_ner)=

## spaCy-Based Named Entity Recognizer （spaCyを用いた固有表現抽出ブロック）

(`dialbb.builtin_blocks.ner_with_spacy.ne_recognizer.SpaCyNER`)

(ver0.6で追加）

[spaCy](https://spacy.io)および[GiNZA](https://megagonlabs.github.io/ginza/)を用いて固有表現抽出を行います．

### 入出力

- 入力

  - `input_text`: 入力文字列（文字列）
  - `aux_data`: 補助データ（辞書型）

- 出力

  - `aux_data`: 補助データ（辞書型）

    入力された`aux_data`に固有表現抽出結果を加えたものです．

    固有表現抽出結果は，以下の形です．

    ```json
    {"NE_<ラベル>": "<固有表現>", "NE_<ラベル>": "<固有表現>", ...}
    ```

    <ラベル>は固有表現のクラスです．固有表現は見つかった固有表現で，`input_text`の部分文字列です．同じクラスの固有表現が複数見つかった場合，`:`で連結します．

    例

    ```json
    {"NE_Person": "田中:鈴木", "NE_Dish": "味噌ラーメン"}
    ```

    固有表現のクラスについては，spaCy/GiNZAのモデルのサイトを参照してください．

    - `ja-ginza-electra` (5.1.2):，[https://pypi.org/project/ja-ginza-electra/](https://pypi.org/project/ja-ginza-electra/) 
    - `en_core_web_trf` (3.5.0):，[https://spacy.io/models/en#en_core_web_trf-labels](https://huggingface.co/spacy/en_core_web_trfhttps://pypi.org/project/ja-ginza-electra/)

### ブロックコンフィギュレーションのパラメータ

- `model` (文字列．必須）

  spaCy/GiNZAのモデルの名前です．`ja_ginza_electra` (日本語），`en_core_web_trf` (英語）などを指定できます．

- `patterns` (オブジェクト．任意）

  ルールベースの固有表現抽出パターンを記述します．パターンは，[spaCyのパターンの説明](https://spacy.io/usage/rule-based-matching)に書いてあるものをYAML形式にしたものです．

  以下が日本語の例です．

  ```yaml
  patterns: 
    - label: Date
      pattern: 昨日
    - label: Date
      pattern: きのう
  ```

### 処理内容

spaCy/GiNZAを用いて`input_text`中の固有表現を抽出し，`aux_data`にその結果を入力して返します．
