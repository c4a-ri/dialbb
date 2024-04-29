#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# run_server.py
#   invoke the dialogue application server
#
__version__ = '0.1'
__author__ = 'Mikio Nakano'

import argparse
from dialbb.server.run_server import start_dialbb


def main(config_file, port):

    # starts dialbb/server/run_server
    start_dialbb(config_file, port)


if __name__ == '__main__':
    # read arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="config yaml file")
    parser.add_argument("--port", help="port number", default=8080)
    args = parser.parse_args()

    main(args.config, args.port)
