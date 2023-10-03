#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# user_spoke_gui.py
#   user spoke for a multi-party dialogue system with GUI
#
import socketio
import argparse
import PySimpleGUI as sg


my_name: str = ""

sio = socketio.Client()


@sio.event
def connect():
    print('connection established')


@sio.event
def disconnect():
    print('disconnected from server')


@sio.on('broadcast_utterance')
def receive_utterance(data):

    global dialogue_history
    new_utterance = f"{data['speaker']}:{data['utterance']}"
    if dialogue_history:
        dialogue_history += "\n" + new_utterance
    else:
        dialogue_history = new_utterance
    window.refresh()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('my_name', type=str)
    args = parser.parse_args()

    my_name = args.my_name

    sio.connect('http://localhost:5000')

    dialogue_history = ""
    layout = [[sg.Text(f'Your name: {my_name}'), sg.Button('Join')],
              [sg.Text('Input your utterance'), sg.InputText(key='-utterance-', size=(80, 1)), sg.Button('Send')],
              [sg.Output(size=(120, 30), key='-dialogue_history-')]]

    # Create the Window
    window = sg.Window('Window Title', layout, resizable=True)
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read(timeout=100, timeout_key='-timeout-')
        if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
            break

        if event == 'Join':
            sio.emit('join', {'speaker': my_name, 'utterance': ""})
        elif event == 'Send':
            utterance = values['-utterance-']
            sio.emit('utterance', {'speaker': my_name, 'utterance': utterance})
        elif event == '-timeout-':
            window['-dialogue_history-'].update(dialogue_history)






