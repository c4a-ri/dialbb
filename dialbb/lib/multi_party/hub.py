#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# hub.py
#   hub for multi-party dialogue
#
__version__ = '0.1'
__author__ = 'Mikio Nakano'

import argparse
import sys

import eventlet
import socketio
import yaml
from typing import List

sio = socketio.Server()
app = socketio.WSGIApp(sio)

participants: List[str] = []
participants_who_joined: List[str] = []


@sio.event
def connect(sid, environ):
    print('connect ', sid)


@sio.event
def my_message(sid, data):
    print('message ', data)


@sio.event
def disconnect(sid):
    print('disconnect ', sid)


@sio.on('join')
def on_utterance(sid, data):
    print(f"{data['speaker']} joined.", flush=True)
    participants_who_joined.append(data['speaker'])

    # check every participant joined
    everyone_is_here = True
    for participant in participants:
        if not participant in participants_who_joined:
            everyone_is_here = False
            break
    if everyone_is_here:
        print('Everyone is here.')
        sio.emit('start_conversation', {})


@sio.on('utterance')
def on_utterance(sid, data):
    print(str(data))
    print(f"utterance received from {data['speaker']}: {data['utterance']}", flush=True)
    sio.emit('broadcast_utterance', {'speaker': data['speaker'], 'utterance': data['utterance']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str)
    args = parser.parse_args()
    config_file = args.config
    with open(config_file, encoding='utf-8') as fp:
        config = yaml.safe_load(fp)

    if not config.get('participants'):
        print("no participant information in the config.")
        sys.exit(1)
    for participant in config['participants']:
        participants.append(participant['name'])
        participants_who_joined = []  # initialize

    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)











