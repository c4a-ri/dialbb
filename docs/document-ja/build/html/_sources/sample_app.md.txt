# 日本語サンプルアプリケーションの説明

本節では，`sample_apps/network_ja`にあるサンプルアプリケーションを通して，DialBBアプリケーションの構成を説明します．

`sample_apps/network_ja`ディレクトリ（フォルダ）をコピーして編集することで，違うアプリケーションを作ることができます．どこにコピーしても構いません．

## ファイル構成

sample_apps/network_jaには以下のファイルが含まれています．

| ファイル名               | 説明                                                         |
| ------------------------ | ------------------------------------------------------------ |
| config.yml               | アプリケーションを規定するconfigurationファイル              |
| sample-knowledge-ja.xlsx | 言語理解ブロック，対話管理ブロックで用いる知識を記述したもの |
| scenario_functions.py    | 対話管理ブロックで用いるプログラム                           |
| test_inputs.json         | システムテストで使うデータ                                   |

## システム構成とコンフィギュレーション

### 入出力

- ここではDialBBのアプリケーションの入出力のデータ構造を説明します．なお，ブラウザから接続して使う場合，これらのデータ構造を意識する必要はありません．

- 各ターン（一回の発話のやりとりのこと）での入力は以下のような辞書形式のデータです．

  - 対話開始時

    ```json
    {
      "user_id": <ユーザID: 文字列>,
      "aux_data": <補助データ：データ型は任意>
    }
    ```

  - 対話開始後

    ```json
    {
       "user_id": <ユーザID：文字列>,
       "session_id": <セッションID：文字列>,
       "user_utterance": <ユーザ発話：文字列>,
       "aux_data":<補助データ：データ型は任意>
    }
    ```

- 各ターンでの出力は以下のような辞書形式のデータです．

    ```json
    {
      "session_id":<セッションID: 文字列>,
      "system_utterance",<システム発話文字列: 文字列>, 
      "user_id":<ユーザID: 文字列>, 
      "final": <対話終了フラグ: ブール値> 
      "aux_data": <補助データ: オブジェクト>
    }
    ```

### ブロック

本アプリケーションでは，以下の3つの組み込みブロックを利用しています．

- Utterance canonicalizer: ユーザ入力文の正規化（大文字→小文字，全角⇒半角の変換など）を行います．

- SNIPS understander: 言語理解を行います．
  [SNIPS_NLU](https://snips-nlu.readthedocs.io/en/latest/)を利用して，ユーザ発話タイプ（インテントとも呼びます）の決定とスロットの抽出を行います．
  
- STN manager: 状態遷移ネットワーク(State-Transition Network)を用いて対話管理を行います．

組み込みブロックとは，DialBBにあらかじめ含まれているブロックです．
これらの組み込みブロックの詳細は，{ref}`builtin_blocks`で説明しています．

本アプリケーションは以下のようなシステム構成をしています．

![sample-arch](../../images/sample-arch.jpg)

### コンフィギュレーション

本アプリケーションのコンフィギュレーションファイルは以下のようなyamlファイルです．

```yml
language: ja   # 言語を指定

blocks:  # ブロックのリスト
  - name: canonicalizer  # ブロック名
    # ブロックのクラス
    block_class: preprocess.utterance_canonicalizer.UtteranceCanonicalizer 
    input: # ブロックへの入力
      input_text: user_utterance
    output: # ブロックからの出力
      output_text: canonicalized_user_utterance
  - name: understander
    block_class: understanding_with_snips.snips_understander.Understander
    input:
      input_text: canonicalized_user_utterance
    output: 
      nlu_result: nlu_result
    knowledge_file: sample-knowledge-ja.xlsx  # 知識記述ファイル
  - name: manager
    block_class: stn_management.stn_manager.Manager
    knowledge_file: sample-knowledge-ja.xlsx # 知識記述ファイル
    function_definitions: scenario_functions  # 知識記述の中で用いる関数の定義ファイル
    input:
      sentence: canonicalized_user_utterance
      nlu_result: nlu_result
      user_id: user_id
      session_id: session_id
    output:
      output_text: system_utterance
      final: final
```

`blocks`要素は各ブロックのコンフィギュレーションのリストです．この順に処理が行われます．

`name`はブロックの名前で，ロギングなどに使われます．

`block_class`はブロックのクラス名です．このアプリケーションではあらかじめ用意してあるクラスのみを使います．

`input`と`output`は，ブロックへの入出力を規定します．‘：‘の左側がブロック内で参照するためのキーで，右側がpayloadでのキーです．例えば，`canonicalizer`ブロックの出力の`output_text`要素がpayloadの`canonicalized_user_utterance`要素の値になり，これが，`understander`ブロックへの入力の`input_text`要素になります．

これらの要素に加え，各ブロックのコンフィギュレーションでは，ブロック独自の要素を持つことができます．例えば，`understander`や`manager`には`knowledge_file`要素が，`manager`には`function_definition`要素があります．これらをどう使うかは，ブロックのクラス定義の中で決められています．

## 言語理解

### 言語理解結果

言語理解ブロックは，入力発話を解析し，タイプとスロットを抽出します．

例えば，「好きなのは醤油」の言語理解結果は次のようになります．

```json
{"type": "特定のラーメンが好き", "slots": {"favarite_ramen": "醤油ラーメン"}}
```

`"特定のラーメンが好き"`がタイプで，`"favarite_ramen"`スロットの値が`"醤油ラーメン"`です．複数のスロットを持つような発話もあり得ます．

### 言語理解知識

言語理解用の知識は，`sample-knowledge-ja.xlsx`に書かれています．

言語理解知識は，以下の４つのシートからなります．

| シート名   | 内容                                   |
| ---------- | -------------------------------------- |
| utterances | タイプ毎の発話例                       |
| slots      | スロットとエンティティの関係           |
| entities   | エンティティに関する情報               |
| dictionary | エンティティ毎の辞書エントリーと同義語 |

これらの詳細は「{ref}`nlu_knowledge`」を参照してください．

### SNIPS用の訓練データ

アプリを立ち上げると上記の知識はSNIPS用の訓練データに変換され，モデルが作られます．

SNIPS用の訓練データはアプリのディレクトリの`_training_data.json`です．このファイルを見ることで，うまく変換されているかどうかを確認できます．

## 対話管理

対話管理知識（シナリオ）は，`sample-knowledge-ja.xlsx`ファイルの`scenario`シートです．
このシートの書き方の詳細は「{ref}`scenario`」を参照してください．

Graphvizがインストールされていれば，アプリケーションを起動したとき，シナリオファイルから生成した状態遷移ネットワークの画像ファイルを出力します．以下が本アプリケーションの状態遷移ネットワークです．

![sample-ja-stn-graph](../../images/sample-ja-stn-graph.jpg)


シナリオファイルで用いている遷移の条件や遷移後に実行する関数のうち，組み込み関数でないものが
`scenario_functions.py`で定義されています．






