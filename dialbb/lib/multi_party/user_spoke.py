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
my_name: str = ""


@sio.event
def connect():
    print('connection established')

@sio.event
def disconnect():
    print('disconnected from server')


@sio.on('broadcast_utterance')
def receive_utterance(data):
    print(f"\r{data['speaker']}:{data['utterance']}> \nyou>", flush=True, end='')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('my_name', type=str)
    args = parser.parse_args()

    my_name = args.my_name

    sio.connect('http://localhost:5000')

    # join the conversation
    initial_utterance: str = input('press enter to join the conversation>')
    sio.emit('join', {'speaker': my_name, 'utterance': ""})

    while True:
        input_utterance: str = input('you>')
        sio.emit('utterance', {'speaker': my_name, 'utterance': input_utterance})





