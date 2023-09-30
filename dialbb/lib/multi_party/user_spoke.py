#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# user_spoke.py
#   user spoke for a multi-party dialogue system
#
import os
import socketio
import argparse


sio = socketio.Client()


@sio.event
def connect():
    print('connection established')

@sio.event
def disconnect():
    print('disconnected from server')


@sio.on('broadcast_utterance')
def receive_utterance(data):
    print(f"\r{data['participant']}:{data['utterance']}> \nyou>", flush=True)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int)
    parser.add_argument('participant_id', type=str)
    args = parser.parse_args()

    participant_id = args.participant_id

    sio.connect('http://localhost:5000')

    initial_utterance: str = input('press enter to join the conversation>')
    sio.emit('join', {'participant_id': participant_id, 'utterance': ""})
    while True:
        input_utterance: str = input('you>')
        sio.emit('utterance', {'participant_id': participant_id, 'utterance': input_utterance})





