# DialBB多人数会話サンプルアプリケーション


## サンプルアプリの起動方法

以下、このREADMEをおいてあるディレクトリで行う


- ライブラリのインストール

  ```sh
  pip install -r requirements.txt
  ```

- ハブの起動

  ```sh
  export DIALBB_HOME=../..
  export PYTHONPATH=$DIALBB_HOME
  python $DIALBB_HOME/dialbb/lib/multi_party/hub.py mp_config.yml
  ```

- 参加者1のシステムの起動（田中）


  別ウインドウを開き、以下を行う

  ```sh
  export OPENAI_KEY=<OpenAI API Key>
  export DIALBB_DEBUG=yes
  export DIALBB_HOME=../..
  export PYTHONPATH=$DIALBB_HOME
  python $DIALBB_HOME/dialbb/lib/multi_party/dialbb_spoke.py config1.yml 田中
  ```

- 参加者2のシステムの起動（鈴木）


  別ウインドウを開き、以下を行う

  ```sh
  export OPENAI_KEY=<OpenAI API Key>
  export DIALBB_DEBUG=yes
  export DIALBB_HOME=../..
  export PYTHONPATH=$DIALBB_HOME
  python $DIALBB_HOME/dialbb/lib/multi_party/dialbb_spoke.py config2.yml 鈴木
  ```

- 参加者3として人間が参加するためのシステムの起動（参加者名：山田）


  別ウインドウを開き、以下を行う

  ```sh
  export DIALBB_DEBUG=yes
  export DIALBB_HOME=../..
  export PYTHONPATH=$DIALBB_HOME
  python $DIALBB_HOME/dialbb/lib/multi_party/user_spoke_gui.py 山田
  ```

- 参加者3もDialBBアプリの場合


  別ウインドウを開き、以下を行う

  ```sh
  export OPENAI_KEY=<OpenAI API Key>
  export DIALBB_DEBUG=yes
  export DIALBB_HOME=../..
  export PYTHONPATH=$DIALBB_HOME
  python $DIALBB_HOME/dialbb/lib/multi_party/dialbb_spoke.py config3.yml 山田
  ```

