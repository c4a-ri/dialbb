#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# user_spoke.py
#   User spoke for a multi-party dialogue system
#   This works on a command line
#

import socketio
import argparse

#  socket io client
sio = socketio.Client()
my_name: str = ""


# connected
@sio.event
def connect():
    print('connection established')


# disconnection
@sio.event
def disconnect():
    print('disconnected from server')


# disconnection
@sio.on('broadcast_utterance')
def receive_utterance(data):
    print(f"\r{data['speaker']}:{data['utterance']}> \nyou>", flush=True, end='')


# main process
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('my_name', type=str)
    args = parser.parse_args()

    # participant name
    my_name = args.my_name

    sio.connect('http://localhost:5000')

    # join the conversation
    initial_utterance: str = input('press enter to join the conversation>')
    sio.emit('join', {'speaker': my_name, 'utterance': ""})

    while True:
        input_utterance: str = input('you>')
        sio.emit('utterance', {'speaker': my_name, 'utterance': input_utterance})





