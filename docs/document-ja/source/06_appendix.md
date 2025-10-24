# Appendix

## フロントエンド

DialBBには，Web APIにアクセスするための，2種類のサンプルフロントエンドが付属しています．

### シンプルなフロントエンド

以下でアクセスできます．

```
http://<ホスト>:<ポート番号>
```

システム発話とユーザ発話を吹き出しで表示します．

`aux_data`の送信はできません．また，レスポンスに含まれるシステム発話以外の情報は表示されません．

### デバッグ用フロントエンド

以下でアクセスできます．

```
http://<ホスト>:<ポート番号>/test
```

システム発話とユーザ発話をリスト型式で表示します．

`aux_data`の送信ができます．また，レスポンスに含まれる`aux_data`も表示されます．



## DialBBをpipでインストールせずに利用する方法

GitHubリポジトリからcloneします．cloneしたディレクトリを<DialBBのディレクトリ>とします．

```sh
git clone git@github.com:c4a-ri/dialbb.git <DialBBのディレクトリ>
```

環境変数`PYTHONPATH`を設定します．

```sh
export PYTHONPATH=<DialBBのディレクトリ>:$PYTHONPATH
```

クラスAPIで利用する場合，Pythonを立ち上げた後`dialbb`から必要なモジュールやクラスをimportします．

```python
from dialbb.main import DialogueProcessor
```

WebAPIで利用する場合，コンフィギュレーションファイルを指定してサーバを起動します．

```sh
$ python <DialBBのディレクトリ>/run_server.py [--port <port>] <config file>
```

`port`（ポート番号）のデフォルトは8080です．




## ユーザシミュレータを用いたテスタ

LLM (ChatGPT) を用いたユーザシミュレータを用いたテスタが付属しています。

### サンプルの動かし方

以下bashの例で説明します．Windows コマンドプロンプトの場合は適宜読み替えてください。

- DialBBをインストールし、サンプルアプリケーションをダウンロードして展開します．

- 環境変数`OPENAI_API_KEY`にOpenAI APIのキーを設定します．

  ```sh
  export OPENAI_KEY=<OPENAIのAPIキー>
  ```

- サンプルアプリケーションを展開したディレクトリ（`sample_apps`）で以下のコマンドを実行します．

  ```sh
  dialbb-tester --app_config lab_app_ja/config.yml --test_config lab_app_ja/simulation/config.yml --output _output.txt
  ```
  
- `_output.txt`に結果が記述されます．

- プログラムの中でテスタを起動するには以下のようにします

  ```python
  from dialbb.sim_tester.main import test_by_simulation
  
  test_by_simulation("lab_app_ja/config.yml", 
                     "lab_app_ja/simulation/config.yml", output="_output.txt")
  ```


### 仕様

- 起動オプション

  ```sh
  dialbb-tester --app_config <DialBBアプリケーションのコンフィギュレーションファイル> --test_config <テストコンフィギュレーションファイル> --output <出力ファイル>
  ```
  
- テストコンフィギュレーションファイル

  以下のキーをもつYAML
  
  - `model`: （文字列．必須）OpenAIのGPTモデル名．`gpt-4o`，`gpt-4o-mini`など．`gpt-5`は不可．
  - `user_name`: （文字列．任意）プロンプト内の対話履歴でユーザを指す文字列．デフォルト値 "User"
  - `system_name`: （文字列．任意）プロンプト内の対話履歴でシステムを指す文字列．デフォルト値 "System"
  - `settings`（オブジェクトのリスト．必須）設定のリスト．以下の要素を持つことができる
  
    - `prompt_templates`: （文字列のリスト．必須）プロンプトテンプレートを記述したテキストファイルのパスのリスト．ファイルパスはコンフィギュレーションファイルからの相対パス．
  
    - `initial_aux_data`（文字列．任意）対話の最初にDialBBアプリケーションにアクセスする際に，`aux_data`に入れる内容を書いたJSONファイルのパス．パスはコンフィギュレーションファイルからの相対パス．
  - `temperatures`: （浮動小数点数のリスト．任意）GPTの温度パラメータのリスト．デフォルト値は0.7の一要素のみのリスト．`prompt_templates`のリストの長さ×このリストの長さのセッションが行われます．
  - `max_turns`: (整数．任意）セッションあたりの最大ターン数．デフォルト値15．
  
- 関数仕様

  - `dialbb.sim_test.main.test_by_simulation(test_config_file: str, app_config_file: str, output_file: str=None, json_output: bool=False, prompt_params: Dict[str, str])`

    パラメータ
    
    - `test_config_file`: テストコンフィギュレーション

    - `app_config_file`: DialBBアプリケーションファイル

    - `output_file`: 対話ログ出力ファイル
  
    - `json_output`: 出力ファイルのフォーマットがJSONかどうか。Falseならテキストファイル。

    - `prompt_params`: プロンプトに埋め込む情報を辞書型で記述したもの。プロンプトテンプレートに`{<key>}`があれば、`<value>`で置き換えられる。

## 廃止された機能

### Snips Understander組み込みブロック

SnipsがPython3.9以上ではインストールが困難なため，ver. 0.9で廃止されました．代わりにLR-CRF Understander組み込みブロックを用いてください．

### Whitespace Tokenizer組み込みブロックおよびSudachi Tokenizer組み込みブロック

ver. 0.9で廃止されました．LR-CRF UnderstanderやChatGPT Understanderを使えばTokenizerブロックを使う必要はありません．

### Snips+STNサンプルアプリケーション

ver. 0.9で廃止されました．

