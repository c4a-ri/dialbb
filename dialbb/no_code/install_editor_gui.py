#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 C4A Research Institute, Inc.
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
# install_editor_gui.py
#   copy scenario editor GUI to a proper place

import argparse
import zipfile
import dialbb
import os

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("editor_gui_zip_file", help="Editor GUI zip file")
    args = parser.parse_args()

    editor_dir = os.path.join(os.path.dirname(dialbb.__file__), 'no_code/gui_editor')

    with zipfile.ZipFile(args.editor_gui_zip_file) as zf:
        zf.extractall(editor_dir)

    print(f"Scenario editor GUI has been installed at: {editor_dir}.")
