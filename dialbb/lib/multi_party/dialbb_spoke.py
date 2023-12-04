#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# spoke_with_dialbb.py
#   spoke for multi-party dialogue that uses a DialBB app
#

from typing import Dict, Any, List

import socketio
import argparse
from dialbb.main import DialogueProcessor

session_id = ""
my_name = ""

sio = socketio.Client()


@sio.event
def connect():
    print('connection established')


@sio.on('start_conversation')
def receive_utterance(data):
    global session_id
    print('conversation started', flush=True)
    participants: List[str] = data['participants']
    initial_response: Dict[str, Any] = dialogue_processor.process({"user_id": "",
                                                                   "aux_data": {"participants": participants}},
                                                                  initial=True)
    session_id = initial_response['session_id']
    system_utterance: str = initial_response['system_utterance']
    if initial_response['system_utterance']:
        sio.emit('utterance', {'speaker': my_name, 'utterance': system_utterance})


@sio.on('broadcast_utterance')
def receive_utterance(data):
    print('utterance received:', data['utterance'], flush=True)
    if data['speaker'] != my_name:
        response: Dict[str, Any] = dialogue_processor.process({"user_id": data['speaker'],
                                                               "user_utterance": data['utterance'],
                                                               "session_id": session_id
                                                               })
        system_utterance: str = response['system_utterance']
        if response['system_utterance']:
            sio.emit('utterance', {'speaker': my_name, 'utterance': system_utterance})


@sio.on('silence_detected')
def receive_utterance(data):
    print('utterance received:', data['utterance'], flush=True)
    if data['speaker'] != my_name:
        response: Dict[str, Any] = dialogue_processor.process({"user_id": data['speaker'], "session_id": session_id})
        system_utterance: str = response['system_utterance']
        if response['system_utterance']:
            sio.emit('utterance', {'speaker': my_name, 'utterance': system_utterance})


@sio.event
def disconnect():
    print('disconnected from server')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', type=str)
    parser.add_argument('my_name', type=str)
    args = parser.parse_args()

    my_name = args.my_name

    dialogue_processor = DialogueProcessor(args.config_file, {"my_name": my_name})

    sio.connect('http://localhost:5000')
    sio.emit('join', {'speaker': my_name, 'utterance': ""})
    sio.wait()
