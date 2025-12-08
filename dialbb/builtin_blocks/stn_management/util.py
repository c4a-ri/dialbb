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
# util.py
#   utilities for STN manager, e.g., logger


from dialbb.util.globals import DEBUG
from dialbb.util.logger import get_logger
from typing import Dict, Any

scenario_function_logger = get_logger("scenario_function")


def scenario_function_log_debug(message: str, context: Dict[str, Any]) -> None:

    scenario_function_logger.debug(f"session: {context.get('_session_id', 'unknown')}, {message}")


def scenario_function_log_info(message: str, context: Dict[str, Any]) -> None:

    scenario_function_logger.info(f"session: {context.get('_session_id', 'unknown')}, {message}")


def scenario_function_log_warning(message: str, context: Dict[str, Any]) -> None:

    scenario_function_logger.warning(f"session: {context.get('_session_id', 'unknown')}, {message}")


def scenario_function_log_error(message: str, context: Dict[str, Any]) -> None:

    scenario_function_logger.error(f"session: {context.get('_session_id', 'unknown')}, {message}")
    if DEBUG:
        raise Exception(message)

