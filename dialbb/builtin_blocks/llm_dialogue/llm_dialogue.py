# llm_dialogue.py
#   performs dialogue using various LLMs via LangChain
#   LangChainを用いて様々なLLMで対話

__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import os
import sys
import traceback
import datetime
from typing import Dict, Any, List, Union, Tuple
from langchain.chat_models import init_chat_model
from dialbb.abstract_block import AbstractBlock
from dialbb.builtin_blocks.util import extract_aux_data
from dialbb.util.error_handlers import abort_during_building
import re

from dialbb.util.globals import CHATGPT_INSTRUCTIONS

DIALOGUE_HISTORY_OLD_TAG: str = '@dialogue_history'
DIALOGUE_HISTORY_TAG: str = '{dialogue_history}'
CURRENT_TIME_TAG: str = '{current_time}'
DIALOGUE_UP_TO_NOW = {"ja": "現在までの対話", "en": "Dialogue up to now"}
DEFAULT_LLM: str = "gpt-4o-mini"

REMAINING_TAGS_PATTERN = re.compile( r"\[\[\[(?=.*\{[A-Za-z0-9_]+\})(?:[^\{\]]|\{[A-Za-z0-9_]+\})*\]\]\]", re.DOTALL)

class LLMDialogue(AbstractBlock):
    """
    performs dialogue using various LLMs via LangChain
    """

    def __init__(self, *args):
        super().__init__(*args)

        self._model = self.block_config.get("model", DEFAULT_LLM)
        self._temperature = self.block_config.get("temperature", 0.7)
        self._language = self.config.get("language", 'en')
        self._instruction = self.block_config.get("instruction", CHATGPT_INSTRUCTIONS[self._language])
        self.user_name: str = self.block_config.get("user_name", 'ユーザ' if self._language == 'ja' else "User")
        self.system_name: str = self.block_config.get("system_name", 'システム' if self._language == 'ja' else "System")
        prompt_template_file: str = self.block_config.get("prompt_template", "")
        if not prompt_template_file:
            abort_during_building("prompt template file is not specified")
        filepath: str = os.path.join(self.config_dir, prompt_template_file)
        with open(filepath, encoding='utf-8') as fp:
            self._prompt_template = fp.read()
        if self._prompt_template.find(DIALOGUE_HISTORY_TAG) >= 0 \
           or self._prompt_template.find(DIALOGUE_HISTORY_OLD_TAG) >= 0:
            abort_during_building("The format of the prompt template is obsolete. " +
                                  "The 'dialogue_history' tag is no longer necessary.")
        try:
            if self._model.startswith('gpt-5') or self._model.startswith('openai:gpt-5'):
                self.log_warning("Note that temperature can't be specified for GPT-5x.")
                self._llm = init_chat_model(self._model)
            else:
                self._llm = init_chat_model(self._model, temperature=self._temperature)
        except ImportError:
            abort_during_building(
                "langchain and the provider integration packages must be installed. "
                "Required packages depend on the model provider, for example "
                "langchain-openai, langchain-google-genai, or langchain-huggingface."
            )
        except Exception as e:
            abort_during_building(f"Failed to initialize chat model '{self._model}': {e}")

    def process(self, input_data: Dict[str, Any], session_id: str) -> Union[Dict[str, Union[dict, Any]], str]:
        dialogue_history = input_data.get("dialogue_history")
        if not dialogue_history:
            self.log_error("dialogue_history is not specified as input in the block configuration.")
        aux_data = input_data.get("aux_data", {})
        if aux_data is None:
            aux_data = {}
        if len(dialogue_history) == 1:
            system_utterance = self.block_config.get("first_system_utterance")
            aux_data = input_data.get('aux_data', {})
            final = False
        else:
            system_utterance, aux_data, final = self.generate_system_utterance(dialogue_history, aux_data, session_id)
        return {"system_utterance": system_utterance,
                "aux_data": aux_data,
                "final": final}

    @staticmethod
    def get_current_time_string(language: str) -> str:
        now = datetime.datetime.now()
        if language == 'ja':
            weekdays = ["月", "火", "水", "木", "金", "土", "日"]
            date_str = now.strftime("%Y年%m月%d日")
            time_str = now.strftime("%H時%M分%S秒")
            weekday_str = weekdays[now.weekday()]
            result: str = f"{date_str}（{weekday_str}） {time_str}"
        else:
            result = now.strftime("%A, %B %d, %Y %I:%M:%S %p")
        return result

    def generate_system_utterance(
            self,
            dialogue_history: List[Dict[str, str]],
            aux_data: Dict[str, Any],
            session_id: str
    ) -> Tuple[str, Dict[str, Any], bool]:
        language = self.config.get("language", 'en')
        prompt = self._prompt_template
        prompt = prompt.replace(CURRENT_TIME_TAG, self.get_current_time_string(language))
        if aux_data:
            for aux_data_key, aux_data_value in aux_data.items():
                prompt = prompt.replace("{" + aux_data_key + "}", str(aux_data_value))
        prompt = REMAINING_TAGS_PATTERN.sub("", prompt)
        prompt = prompt.replace('[[[', "")
        prompt = prompt.replace(']]]', "")
        dialogue_history_string: str = ""
        for turn in dialogue_history:
            if turn["speaker"] == 'user':
                dialogue_history_string += f"{self.user_name}: {turn['utterance']}\n"
            else:
                dialogue_history_string += f"{self.system_name}: {turn['utterance']}\n"
        if prompt.find(DIALOGUE_HISTORY_TAG) >= 0:
            prompt: str = self._prompt_template.replace(DIALOGUE_HISTORY_TAG, dialogue_history_string)
        elif prompt.find(DIALOGUE_HISTORY_OLD_TAG) >= 0:
            prompt: str = prompt.replace(DIALOGUE_HISTORY_OLD_TAG, dialogue_history_string)
        else:
            prompt += f"\n#{DIALOGUE_UP_TO_NOW[language]}\n\n{dialogue_history_string}"

        messages = []
        messages.append({'role': "system", "content": self._instruction})
        messages.append({'role': "user", "content": prompt})
        self.log_debug("messages: " + str(messages), session_id=session_id)

        # call LLM
        try:
            response = self._llm.invoke(messages)
            generated_utterance = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            self.log_error("LLM Error: " + traceback.format_exc())
            sys.exit(1)
        self.log_debug("generated system utterance: " + generated_utterance, session_id=session_id)
        system_utterance, aux_data_to_update = extract_aux_data(generated_utterance)
        aux_data.update(aux_data_to_update)
        return system_utterance.strip(), aux_data, False
