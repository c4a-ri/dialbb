#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# llm_selector.py
#   Select the type of LLM model.
#   LLMモデルの切り替え

__version__ = "0.1"
__author__ = "Mikio Nakano"
__copyright__ = "C4A Research Institute, Inc."

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


# LLM base class
class llmBase:
    llm = None

    def __init__(self, model_name: str):
        # Create LLM model
        self.llm = self.create_model(model_name)

    # Create LLM model
    def create_model(self, model_name: str):
        # Generate the LLM model
        raise NotImplementedError

    # Get LLM model
    def get_model(self):
        return self.llm


# ChatGPT model
class llm_chatgpt(llmBase):
    def __init__(self, model_name: str):
        super().__init__(model_name)

    # Create LLM model
    def create_model(self, model_name: str):
        # Generate the model
        return ChatOpenAI(
            model_name=model_name,
            temperature=0.0,
        )


# Google Gemini model
class llm_gemini(llmBase):
    def __init__(self, model_name: str):
        super().__init__(model_name)

    # Create LLM model
    def create_model(self, model_name: str):
        # Generate the model
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.0,
        )


# LLM model selection function
def llm_selector(kind, model_name: str):
    # To add a support model, create it by inheriting the llmBase class.
    classes = {"chatgpt": llm_chatgpt, "gemini": llm_gemini}

    # Select the type of LLM model
    if kind in classes:
        return classes[kind](model_name).get_model()
    raise ValueError(f"Invalid kind: {kind}")
