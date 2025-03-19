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
# remove_files.py
#   remove files

import sys
import os
import shutil
import stat


def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def main():

    for path in sys.path:
        no_code_dir = os.path.join(path, "dialbb/no_code")
        if os.path.exists(no_code_dir):
            shutil.rmtree(no_code_dir, onerror=remove_readonly)
            print(f"{no_code_dir} has been removed.")
            break

if __name__ == "__main__":
    main()







