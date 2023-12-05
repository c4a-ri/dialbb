# Discourse Client using DialBB

## Installing libraries

```sh
pip install -r requirements.txt
```

## Start

```sh
export OPENAI_KEY=<Open AI API key>
export DIALBB_DEBUG=yes
export DIALBB_HOME=../..
export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
export DISCOURSE_URL=<discourse server URL>
export DISCOURSE_API_KEY=<API key of discourse>
export DISCOURSE_USERNAME=<User ID of discourse account>
export DISCOURSE_TOPIC_ID=<Topic id of discourse (integer)>

python $DIALBB_HOME/dialbb/lib/discourse/client.py config.yml
```

## configuration

