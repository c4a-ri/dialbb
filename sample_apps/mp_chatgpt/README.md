DialBB多人数会話サンプルアプリケーション



ハブの立ち上げ

python $DIALBB_HOME/lib/multi_party/hub.py mp_config.yml

python $DIALBB_HOME/lib/multi_party/spoke_with_dialbb.py config1.yml p1

python $DIALBB_HOME/lib/multi_party/spoke_with_dialbb.py config1.yml p2

python $DIALBB_HOME/lib/multi_party/spoke_with_dialbb.py 8081 p3

DialBBアプリの作り方

最初のシステム発話は""

誰も話さないと

{"use_id", "", utterance, ""}

が送られる

