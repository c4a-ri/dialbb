#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# run_server.py
#   invoke dialogue application server
#
__version__ = '0.1'
__author__ = 'Mikio Nakano'


import os
import json
from jsonschema import validate, ValidationError
import argparse
from flask import Flask, request, jsonify, render_template, make_response

from dialbb.main import DialogueProcessor
from dialbb.util.logger import get_logger

DIALBB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# read json schema files
init_request_schema_file: str = os.path.join(DIALBB_DIR, "schemata/init_request.jsd")
dialogue_request_schema_file: str = os.path.join(DIALBB_DIR, "schemata/dialogue_request.jsd")
for request_schema_file in (init_request_schema_file, dialogue_request_schema_file):
    if not os.path.exists(request_schema_file):
        raise Exception(f"can't find request schema: {request_schema_file}")
with open(init_request_schema_file) as fp:
    init_request_schema = json.load(fp)
with open(dialogue_request_schema_file) as fp:
    dialogue_request_schema = json.load(fp)

print(os.path.join(DIALBB_DIR, 'server/static/new'))
app = Flask(__name__, template_folder=os.path.join(DIALBB_DIR, 'server/static/new'),
            static_folder=os.path.join(DIALBB_DIR, 'server/static/new/assets'))

app.config['JSON_AS_ASCII'] = False
app.logger.propagate = False

logger = None

dialogue_processor = None

@app.route('/')
def index():
    return render_template('index.html')
    #html_content = render_template('index.html')
    #response = make_response(html_content)
    #response.mimetype = 'text/javascript'
    #return response



@app.route('/test')
def test():
    return render_template('test.html')


@app.route("/init", methods=['POST'])  # start dialogue
def init():
    """
    generate initial prompt
    :return:
    """
    request_json = request.json
    logger.info("initial request: " + str(request_json))
    try:
        validate(request_json, init_request_schema)  # throws ValidationError
    except ValidationError as e:
        logger.warning("request is not valid.")
        return jsonify({"message": "bad initial request format."}), 400
    result = jsonify(dialogue_processor.process(request_json, initial=True))
    logger.info("response: " + str(result))
    return result


@app.route("/dialogue", methods=['POST'])
def dialogue():
    request_json = request.json
    logger.info("initial request: " + str(request_json))
    print(f"request: {str(request_json)}")
    # validation with the json schema
    try:
        validate(request_json, dialogue_request_schema)  # throws ValidationError
    except ValidationError as e:
        logger.warning("request is not valid.")
        return jsonify({"message": "bad request format."}), 400
    result = jsonify(dialogue_processor.process(request.json))
    logger.info("response: " + str(result))
    return result


def start_dialbb(config_file: str, port: int) -> None:

    global app, logger, dialogue_processor

    dialogue_processor = DialogueProcessor(config_file)
    logger = get_logger("server")
    logger.propagate = False

    app.run(host="0.0.0.0", port=port)


# Invoked via WSGI on AWS
def start_dialbb_for_wsgi(config_file):
    global logger, dialogue_processor

    dialogue_processor = DialogueProcessor(config_file)
    logger = get_logger("server")
    logger.propagate = False


def main():
    # read arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="config yaml file")
    parser.add_argument("--port", help="port number", default=8080)
    args = parser.parse_args()

    start_dialbb(args.config, args.port)


if __name__ == '__main__':

    main()
