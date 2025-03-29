# dialbb-tester

OpenAI ChatGPTを用いたDialBBアプリケーションのテスタ

## サンプルの動かし方

以下bashの例で説明します．

- DialBBをインストールします．

- 環境変数`OPENAI_KEY`または`OPENAI_API_KEY`にOpenAI APIのキーを設定します．

  ```sh
  export OPENAI_KEY=<OPENAIのAPIキー>
  ```

- このREADMEのあるディレクトリで以下のコマンドを実行します．

  ```sh
  dialbb-tester --app_config sample_apps/chatgpt/config_ja.yml --test_config sample_ja/config.yml --output _output.txt
  ```
  
- `_output.txt`に結果が記述されます．

- プログラムの中でテスタを起動するには以下のようにします

  ```python
  import dialbb
  
  dialbb.sim_tester.test.main("sample_apps/chatgpt/config_ja.yml", 
                              "sample_ja/config.yml", output="_output.txt")
  ```


## 仕様

- 起動オプション

  ```sh
  python main.py --app_config <DialBBアプリケーションのコンフィギュレーションファイル> --test_config <テストコンフィギュレーションファイル> --output <出力ファイル>
  ```
  
- テストコンフィギュレーションファイル

  以下のキーをもつYAML
  
  - `model`: （文字列．必須）OpenAIのGPTモデル名

  - `user_name`: （文字列．任意）プロンプト内の対話履歴でユーザを指す文字列．デフォルト値 "User"

  - `system_name`: （文字列．任意）プロンプト内の対話履歴でシステムを指す文字列．デフォルト値 "System"

  - `settings`（オブジェクトのリスト．必須）設定のリスト．以下の要素を持つことができる

    - `prompt_templates`: （文字列のリスト．必須）プロンプトテンプレートを記述したテキストファイルのパスのリスト．ファイルパスはコンフィギュレーションファイルからの相対パス．プロンプトテンプレートには以下のタグを含めることができる
  
      - `@dialogue_history` 必須．対話履歴に置き換えられます．
  
      - `@task_description` 任意．コンフィギュレーションファイルの`task_description`で指定されたファイルの中身で置き換えられます．
        実行時に以下のような形の値が代入されます．
  
       ```
       <ブロックコンフィギュレーションのsystem_nameの値>: <システム発話>
       <ブロックコンフィギュレーションのuser_nameの値>: <ユーザ発話>
       <ブロックコンフィギュレーションのsystem_nameの値>: <システム発話>
       ...
       <ブロックコンフィギュレーションのuser_nameの値>: <ユーザ発話>
       <ブロックコンフィギュレーションのsystem_nameの値>: <システム発話>
       ```
  
    - `task_description`: （文字列．任意）タスクを記述したテキストファイルのパス．パスはコンフィギュレーションファイルからの相対パス．
  
    - `initial_aux_data`（文字列．任意）対話の最初にDialBBアプリケーションにアクセスする際に，`aux_data`に入れる内容を書いたJSONファイルのパス．パスはコンフィギュレーションファイルからの相対パス．
  
  - `temperatures`: （浮動小数点数のリスト．任意）GPTの温度パラメータのリスト．デフォルト値は0.7の一要素のみのリスト．`prompt_templates`のリストの長さ×このリストの長さのセッションが行われます．
  
  - `max_turns`: (整数．任意）セッションあたりの最大ターン数．デフォルト値15．

- 関数仕様

  ```
  dialbb.sim_tester.test.main(<テストコンフィギュレーション: str>, 
                              <DialBBアプリケーションコンフィギュレーション>,
                              "sample_ja/config.yml", output="_output.txt")
  ```
