(builtin_blocks)=
# 非推奨となった組み込みブロッククラス

ver2.0で以下のブロックは非推奨となりました．

DialBBパッケージをインストールしても，これらのブロックで必要なライブラリがインストールされない可能性があります．

(japanese_canonicalizer)=

## Japanese Canonicalizer （日本語文字列正規化ブロック）

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

## Simple Canonicalizer （単純文字列正規化ブロック）

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


(lr_crf_understander)=
## LR-CRF Understander （ロジスティック回帰と条件付き確率場を用いた言語理解ブロック）

(`dialbb.builtin_blocks.understanding_with_lr_crf.lr_crf_understander.Understander`）

ロジスティック回帰と条件付き確率場を用いて，ユーザ発話タイプ（インテントとも呼びます）の決定とスロットの抽出を行います．

コンフィギュレーションの`language`要素が`ja`の場合は日本語，`en`の場合は英語の言語理解を行います．

本ブロックは，起動時にExcelで記述した言語理解用知識を読み込み，ロジスティック回帰と条件付き確率場のモデルを学習します．

実行時は，学習したモデルを用いて言語理解を行います．

### 入出力

- 入力

  - `input_text`: 入力文字列

   入力文字列は正規化されていると仮定します．

     例："好きなのは醤油"

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

- `flags_to_use`（文字列のリスト）

  各シートの`flag`カラムにこの値のうちのどれかが書かれていた場合に読み込みます．このパラメータがセットされていない場合はすべての行が読み込まれます．

- `num_candidates`（整数．デフォルト値`1`）

  言語理解結果の最大数（n-bestのn）を指定します．

- `canonicalizer` 

  辞書記述を正規化する際に使うプログラムを指定します．

  - `class` （文字列）

    正規化のブロックのクラスを指定します．基本的にアプリケーションで用いる正規化のブロックと同じものを指定します．

- `knowledge_google_sheet` (ハッシュ)

  - Excelの代わりにGoogle Sheetsを用いる場合の情報を記述します．（Google Sheetsを利用する際の設定は[こはたさんの記事](https://note.com/kohaku935/n/nc13bcd11632d)が参考になりますが，Google Cloud Platformの設定画面のUIがこの記事とは多少変わっています．）

    - `sheet_id` （文字列）

      Google SheetのIDです．

    - `key_file`（文字列）

      Goole Sheet APIにアクセスするためのキーファイルをコンフィギュレーションファイルのディレクトリからの相対パスで指定します．

(lr_crf_nlu_knowledge)=

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

(chatgpt_understander_params)=

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

- `gpt_model` (文字列．デフォルト値は`gpt-4o-mini`）

  ChatGPTのモデルを指定します．`gpt-4o`などが指定できます．

- `prompt_template`

  プロンプトテンプレートを書いたファイルをコンフィギュレーションファイルのディレクトリからの相対パスで指定します．

  これが指定されていない場合は，`dialbb.builtin_blocks.understanding_with_chatgpt.prompt_template_ja.PROMPT_TEMPLATE_JA` （日本語）または，`dialbb.builtin_blocks.understanding_with_chatgpt.prompt_template_en.PROMPT_TEMPLATE_EN` （英語）が使われます．

  プロンプトテンプレートは，言語理解をChatGPTに行わせるプロンプトのテンプレートで，`@`で始まる以下の変数を含みます．

  - `@types` 発話タイプの種類を列挙したものです．
  - `@slot_definitions` スロットの種類を列挙したものです．
  - `@examples` 発話例と，タイプ，スロットの正解を書いた，いわゆるfew shot exampleです．
  - `@input` 入力発話です．

  これらの変数には，実行時に値が代入されます．


### 言語理解知識

本ブロックの言語理解知識の記述形式は，LR-CRF Understanderの言語理解知識の記述形式と全く同じです．詳細はLR-CRF Understanderの説明の{numref}`lr_crf_nlu_knowledge`を参照してください．


(chatgpt_dialogue)=

## ChatGPT Dialogue （ChatGPTベースの対話ブロック）

(`dialbb.builtin_blocks.chatgpt.chatgpt.ChatGPT`)


OpenAI社のChatGPTを用いて対話を行います．

{ref}`(llm_dialogue)`と同じですが，ChatGPTのモデルしか使えません．コンフィギュレーションのモデル指定のパラメータは`model`ではなく，`gpt_model`です．


(chatgpt_ner)=
## ChatGPT NER （ChatGPTを用いた固有表現抽出ブロック）

(`dialbb.builtin_blocks.ner_with_chatgpt.chatgpt_ner.NER`）

OpenAI社のChatGPTを用いて，固有表現の抽出を行います．

コンフィギュレーションの`language`要素が`ja`の場合は日本語，`en`の場合は英語の固有表現抽出を行います．

本ブロックは，起動時にExcelで記述した固有表現用知識を読み込み，固有表現のクラスのリスト，各固有表現クラスの説明，各クラスの固有表現の例，抽出例（Few shot example）に変換し，プロンプトに埋め込みます．

実行時は，プロンプトに入力発話を付加してChatGPTに固有表現抽出を行わせます．

### 入出力

- 入力

  - `input_text`: 入力文字列


  - `aux_data`: 補助データ（辞書型)


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
    {"NE_人名": "田中:鈴木", "NE_料理": "味噌ラーメン"}
    ```

(chatgpt_understander_params)=

### ブロックコンフィギュレーションのパラメータ

- `knowledge_file`（文字列）

  固有表現知識を記述したExcelファイルを指定します．コンフィギュレーションファイルのあるディレクトリからの相対パスで記述します．

- `flags_to_use`（文字列のリスト）

  各シートの`flag`カラムにこの値のうちのどれかが書かれていた場合に読み込みます．このパラメータがセットされていない場合はすべての行が読み込まれます．

- `knowledge_google_sheet` (ハッシュ)

  - Excelの代わりにGoogle Sheetを用いる場合の情報を記述します．（Google Sheetを利用する際の設定は[こはたさんの記事](https://note.com/kohaku935/n/nc13bcd11632d)が参考になりますが，Google Cloud Platformの設定画面のUIがこの記事とは多少変わっています．）

    - `sheet_id` （文字列）

      Google SheetのIDです．

    - `key_file`（文字列）

      Goole Sheet APIにアクセスするためのキーファイルをコンフィギュレーションファイルのディレクトリからの相対パスで指定します．

- `gpt_model` (文字列．デフォルト値は`gpt-4o-mini`）

  ChatGPTのモデルを指定します．`gpt-4o`などが指定できます．

- `prompt_template`

  プロンプトテンプレートを書いたファイルをコンフィギュレーションファイルのディレクトリからの相対パスで指定します．

  これが指定されていない場合は，`dialbb.builtin_blocks.ner_with_chatgpt.chatgpt_ner.prompt_template_ja .PROMPT_TEMPLATE_JA` （日本語）または，`dialbb.builtin_blocks.ner_with_chatgpt.chatgpt_ner.prompt_template_en .PROMPT_TEMPLATE_EN` （英語）が使われます．

  プロンプトテンプレートは，言語理解をChatGPTに行わせるプロンプトのテンプレートで，`@`で始まる以下の変数を含みます．

  - `@classes` 固有表現のクラスを列挙したものです．
  - `@class_explanations` 各固有表現クラスの説明を列挙したものです．
  - `@ne_examples` 各固有表現クラスの固有表現の例を列挙したものです．
  - `@ner_examples` 発話例と，固有表現抽出結果の正解を書いた，いわゆるfew shot exampleです．
  - `@input` 入力発話です．

  これらの変数には，実行時に値が代入されます．

(chatgpt_ner_knowledge)=

### 固有表現抽出知識

固有表現抽出知識は，以下の2つのシートからなります．

| シート名   | 内容                                             |
| ---------- | ------------------------------------------------ |
| utterances | 発話と固有表現抽出結果の例                       |
| classes    | スロットとエンティティの関係および同義語のリスト |

シート名はブロックコンフィギュレーションで変更可能ですが，変更することはほとんどないと思いますので，詳細な説明は割愛します．

#### utterancesシート

各行は次のカラムからなります．

- `flag`      

  利用するかどうかを決めるフラグ．`Y` (yes), `T` (test)などを書くことが多いです．どのフラグの行を利用するかはコンフィギュレーションに記述します．

- `utterance` 

  発話例．

- `entities` 

  発話に含まれる固有表現．固有表現を以下の形で記述します．

  ```
  <固有表現クラス>=<固有表現>, <固有表現クラス>=<固有表現>, ... <固有表現クラス>=<固有表現> 
  ```

  以下が例です．

  ```
  人名=太郎, 地名=東京
  ```

  utterancesシートのみならずこのブロックで使うシートにこれ以外のカラムがあっても構いません．

#### classesシート

各行は次のカラムからなります．

- `flag`

  utterancesシートと同じ

- `class` 

  固有表現クラス名．

- `explanation`

  固有表現クラスの説明

- `examples`

  固有表現の例を`','`で連結したものです．


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

