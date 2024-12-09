#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# context_db.py
#   stores and extracts context information in mongo db

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import os
import pickle

from pymongo import MongoClient
from pymongo.collection import Collection
from typing import Dict, Any, Optional

from dialbb.util.error_handlers import abort_during_building

CONFIG_KEY_CONTEXT_DB_HOST: str = "host"
CONFIG_KEY_CONTEXT_DB_PORT: str = "port"
CONFIG_KEY_CONTEXT_DB_USER: str = "user"
CONFIG_KEY_CONTEXT_DB_PASSWORD: str = "password"
KEY_SESSION_ID: str = "session_id"
KEY_CONTEXT: str = "context"
KEY_PREVIOUS_CONTEXT: str = "previous_context"
TEN_MINUTES: int = 10*60*1000
CONTEXT_KEY_CURRENT_STATE_NAME = '_current_state_name'

# context db (to be used when mongo is not used)
context_db = None
# variables
user_information_db = None


class ContextDB:

    def __init__(self, context_db_config: Dict[str, Any]):

        self._debug = True if os.environ.get("CONTEXT_DB_DEBUG", 'no').lower() == "yes" else False

        try:
            mongo_host: str = context_db_config.get(CONFIG_KEY_CONTEXT_DB_HOST)
            if not mongo_host:
                abort_during_building("context db host is not specified.")
            mongo_port: int = int(context_db_config.get(CONFIG_KEY_CONTEXT_DB_PORT, "27017"))
            mongo_user: str = context_db_config.get(CONFIG_KEY_CONTEXT_DB_USER)
            mongo_password: str = context_db_config.get(CONFIG_KEY_CONTEXT_DB_PASSWORD)
            mongo_client = MongoClient(mongo_host,
                                       mongo_port,
                                       username=mongo_user,
                                       password=mongo_password,
                                       maxIdleTimeMS=TEN_MINUTES)
            assert mongo_client is not None
            mongo_context_db = mongo_client.context_db
            self._context_collection: Collection = mongo_context_db.context_collection
        except Exception as e:
            abort_during_building(f"failed to connect the context db.")

    @staticmethod
    def _serialize_context(context: Dict[str, Any]) -> bytes:

        result: bytes = pickle.dumps(context)
        return result

    @staticmethod
    def _deserialize_context(serialized_context: bytes) -> Dict[str, Any]:

        result: Dict[str, Any] = pickle.loads(serialized_context)
        return result

    def add_context(self, session_id: str, context: Dict[str, Any]) -> None:

        if self._debug:
            state: str = context.get(CONTEXT_KEY_CURRENT_STATE_NAME, "")
            print(f"adding context to db (state: {state}): " + str(context))
        serialized_context = self._serialize_context(context)
        if self._context_collection.find_one({KEY_SESSION_ID: session_id}):
            self._context_collection.find_one_and_update({KEY_SESSION_ID: session_id},
                                                         {"$set": {KEY_CONTEXT: serialized_context}})
        else:
            self._context_collection.insert_one({KEY_SESSION_ID: session_id, KEY_CONTEXT: serialized_context})

    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:

        document: Dict[str, Any] = self._context_collection.find_one({KEY_SESSION_ID: session_id})
        if document:
            serialized_context: bytes = document.get(KEY_CONTEXT)
            context: Dict[str, Any] = self._deserialize_context(serialized_context)
            if self._debug:
                state: str = context.get(CONTEXT_KEY_CURRENT_STATE_NAME, "")
                print(f"got context from db  (state: {state}): " + str(context))
            return context
        else:
            if self._debug:
                print("no context found in the db.")
            return None


    def add_previous_context(self, session_id: str, context: Dict[str, Any]) -> None:

        if self._debug:
            state: str = context.get(CONTEXT_KEY_CURRENT_STATE_NAME, "")
            print(f"adding previous context db  (state: {state}): " + str(context))
        serialized_context = self._serialize_context(context)
        if self._context_collection.find_one({KEY_SESSION_ID: session_id}):
            self._context_collection.find_one_and_update({KEY_SESSION_ID: session_id},
                                                         {"$set": {KEY_PREVIOUS_CONTEXT: serialized_context}})
        else:
            self._context_collection.insert_one({KEY_SESSION_ID: session_id, KEY_PREVIOUS_CONTEXT: serialized_context})

    def get_previous_context(self, session_id: str) -> Optional[Dict[str, Any]]:

        document: Dict[str, Any] = self._context_collection.find_one({KEY_SESSION_ID: session_id})
        if document:
            serialized_context: bytes = document.get(KEY_PREVIOUS_CONTEXT)
            context: Dict[str, Any] = self._deserialize_context(serialized_context)
            if self._debug:
                state: str = context.get(CONTEXT_KEY_CURRENT_STATE_NAME, "")
                print(f"got previous context from db  (state: {state}): " + str(context))
            return context
        else:
            if self._debug:
                print("no previous context found in the db.")
            return None

