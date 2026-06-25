#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 C4A Research Institute, Inc.
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
# passage_retrieval.py
#   retrieves passage for RAG
#   RAG用のパッセージ抽出

__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import os
import shutil
from typing import List, Iterable, Dict, Any, Union, Tuple

import unicodedata

from dialbb.abstract_block import AbstractBlock
from dialbb.util.error_handlers import abort_during_building
from pathlib import Path
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_unstructured.document_loaders import UnstructuredLoader

from dialbb.util.globals import DEBUG

DEFAULT_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".docx",
    ".pptx",
    ".html",
    ".htm",
    ".json",
    ".csv",
}


class Retriever(AbstractBlock):
    def __init__(self, *args):
        super().__init__(*args)

        self._language: str = self.config.get('language', 'en')

        # for ingest
        self._vector_db_dir: Path = Path(self.config_dir) / self.block_config.get('vector_db_dir', "vector_db")
        self._collection: str = self.block_config.get('collection', "rag_docs")
        self._clear_before_ingest: bool = self.block_config.get('clear_before_ingest', True)
        chunk_size: int = self.block_config.get('chunk_size', 800)
        chunk_overlap: int = self.block_config.get('chunk_overlap', 100)
        sources: List[str] = self.block_config.get('sources')
        if not sources:
            abort_during_building("RAG sources are not specified.")
        extensions: List[str] = self.block_config.get('extensions', DEFAULT_EXTENSIONS)

        # for search
        self._top_k: int = self.block_config.get('top_k', 5)
        if self._top_k <= 0:
            abort_during_building("top_k must be > 0")

        self._separator: str = self.block_config.get('separator', "\n\n---\n\n")
        self._embeddings = self._get_embeddings()
        if self._clear_before_ingest:
            self._reset_vector_db()
        self._vector_db = self._get_chroma()

        # ingest
        self._ingest(sources, chunk_size, chunk_overlap, extensions)

    def process(self, input_data: Dict[str, Any], session_id: str) -> Union[Dict[str, Union[dict, Any]], str]:
        aux_data = input_data.get("aux_data")
        if not aux_data:
            aux_data = {}
        dialogue_history = input_data.get("dialogue_history")
        if not dialogue_history:
            self.log_error("dialogue_history is not specified as input in the block configuration.")
        else:
            last_user_utterance: str = dialogue_history[-1]["utterance"]
            if last_user_utterance != "":
                passages, docs = self._retrieve_passage(last_user_utterance)
                aux_data["passages"] = passages
        return {"aux_data": aux_data}

    def _retrieve_passage(self, query: str) -> Tuple[str, List]:

        self._logger.debug(f"searching {query}")
        results = self._vector_db.similarity_search(query, k=self._top_k)
        self._logger.debug(f"num results: {len(results)}")
        combined = self._separator.join([d.page_content for d in results])
        self._logger.debug(f"retrieved passages: {combined}")
        return combined, results

    @staticmethod
    def _iter_files(input_path: Path, extensions: List[str]) -> Iterable[Path]:
        """
        list target documents
        """
        if input_path.is_file():
            if input_path.suffix.lower() in extensions:
                yield input_path
            return

        for p in input_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in extensions:
                yield p

    def _ingest(self, sources: List[str], chunk_size: int, chunk_overlap: int, extensions: List[str]) -> None:
        """
        ingest vectors
        :param sources: source directories
        :param chunk_size: chunk size
        :param chunk_overlap: chunk overlap
        :param extensions: extensions for source files
        :return: None
        """

        files = []
        for source in sources:
            source_path = Path(self.config_dir) / source
            files.extend(self._iter_files(source_path, extensions))

        if not files:
            abort_during_building(f"No documents found in: {str(source_path)}")

        raw_docs = self._load_documents(files)
        raw_docs = self._normalize_documents(raw_docs)

        splitter = self._build_splitter(chunk_size, chunk_overlap)
        chunks: List[Document] = splitter.split_documents(raw_docs)
        chunks = filter_complex_metadata(chunks)
        if DEBUG:
            for chunk in chunks:
                print(str(chunk))

        self._vector_db.add_documents(chunks)

    @staticmethod
    def _load_documents(files: List[Path]) -> List:
        docs = []
        for fp in files:
            loader = UnstructuredLoader(str(fp))
            docs.extend(loader.load())
        return docs

    @staticmethod
    def _normalize_documents(docs: List):
        """
        Normalize text for better search/embedding stability.
        Uses NFKC normalization and strips surrounding whitespace.
        """
        for d in docs:
            content = getattr(d, "page_content", None)
            if content:
                d.page_content = unicodedata.normalize("NFKC", content).strip()
        return docs

    @staticmethod
    def _build_splitter(chunk_size: int, chunk_overlap: int) -> CharacterTextSplitter:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")
        return CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    @staticmethod
    def _get_embeddings() -> OpenAIEmbeddings:
        if not os.getenv("OPENAI_API_KEY"):
            abort_during_building("OPENAI_API_KEY environment variable is not set.")
        return OpenAIEmbeddings()

    def _reset_vector_db(self) -> None:
        if self._vector_db_dir.exists():
            shutil.rmtree(self._vector_db_dir)

    def _get_chroma(self) -> Chroma:
        self._vector_db_dir.mkdir(parents=True, exist_ok=True)
        return Chroma(
            collection_name=self._collection,
            persist_directory=str(self._vector_db_dir),
            embedding_function=self._embeddings,
        )



