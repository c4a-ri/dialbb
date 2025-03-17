#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 C4A Research Institute, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
