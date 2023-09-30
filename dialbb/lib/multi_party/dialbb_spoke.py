#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# spoke_with_dialbb.py
#   spoke for multi-party dialogue that uses a DialBB app
#
import sys
from typing import Dict, Any

import socketio
import argparse
from dialbb.main import DialogueProcessor

session_id = ""
participant_id = ""

sio = socketio.Client()


@sio.event
def connect():
    print('connection established')


@sio.on('start_conversation')
def receive_utterance(data):
    print('conversation started', flush=True)
    initial_response: Dict[str, Any] = dialogue_processor.process({"user_id": participant_id}, initial=True)
    session_id: str = initial_response['session_id']
    system_utterance: str = initial_response['system_utterance']
    if initial_response['system_utterance']:
        sio.emit('utterance', {'participant_id': participant_id, 'utterance': system_utterance})


@sio.on('broadcast_utterance')
def receive_utterance(data):
    print('utterance received:', data['utterance'], flush=True)
    if data['participant_id'] != participant_id:
        response: Dict[str, Any] = dialogue_processor.process({"user_id": participant_id,
                                                               "user_utterance": data['utterance'],
                                                               "session_id": session_id
                                                               })
        system_utterance: str = response['system_utterance']
        if response['system_utterance']:
            sio.emit('utterance', {'participant_id': participant_id, 'utterance': system_utterance})


@sio.on('silence_detected')
def receive_utterance(data):
    print('utterance received:', data['utterance'], flush=True)
    if data['participant_id'] != participant_id:
        response: Dict[str, Any] = dialogue_processor.process({"user_id": participant_id, "session_id": session_id})
        system_utterance: str = response['system_utterance']
        if response['system_utterance']:
            sio.emit('utterance', {'participant_id': participant_id, 'utterance': system_utterance})


@sio.event
def disconnect():
    print('disconnected from server')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', type=str)
    parser.add_argument('participant_name', type=str)
    args = parser.parse_args()

    dialogue_processor = DialogueProcessor(args.config_file)

    sio.connect('http://localhost:5000')
    sio.emit('join', {'participant_name': args.participant_name, 'utterance': ""})
    sio.wait()
