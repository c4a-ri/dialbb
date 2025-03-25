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
# uninstall.py
#   uninstall dialbb


import sys
import os
import shutil
import stat


def remove_readonly(func, path, _) -> None:
    """
    Removes read only directory
    :param func: function
    :param path: path to remove
    :param _:
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def main():
    """
    Removes dialbb path from sys.path
    """

    for path in sys.path:
        dialbb_path = os.path.join(path, "dialbb")
        if os.path.exists(dialbb_path):
            shutil.rmtree(dialbb_path, onerror=remove_readonly)
            print(f"{dialbb_path} has been removed.")
            break
    else:
        print(f"dialbb directory was not found in sys.path")


if __name__ == '__main__':
    main()