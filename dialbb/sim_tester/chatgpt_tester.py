import os, sys
import traceback

import openai
from typing import Dict, Any


DEFAULT_GPT_MODEL: str = "gpt-3.5-turbo"
DIALOG_HISTORY_TAG: str = '{dialogue_history}'
DIALOG_HISTORY_OLD_TAG: str = '@dialogue_history'
TIMEOUT: int = 10

class ChatGPTTester:

    def __init__(self, test_config: Dict[str, Any]):

        self._debug = False
        if os.environ.get('DIALBB_TESTER_DEBUG', 'no').lower() == "yes":
            self._debug = True
        openai_key: str = os.environ.get('OPENAI_KEY', os.environ.get('OPENAI_API_KEY', ""))
        if not openai_key:
            print("environment variable OPENAI_KEY or OPENAI_API_KEY is not defined.")
            sys.exit(1)
        self._openai_client = openai.OpenAI(api_key=openai_key)
        openai.api_key = openai_key
        self._gpt_model: str = test_config.get("model", DEFAULT_GPT_MODEL)
        self._prompt_template: str = ""
        self._temperature = 0.7
        self._user_name_string: str = test_config.get("user_name", "User")
        self._system_name_string: str = test_config.get("system_name", "System")
        self._dialogue_history = ""

    def set_parameters_and_clear_history(self, prompt_template: str, temperature: float) -> None:
        """
        setting simulator parameters
        :param prompt_template: template of prompt to be used in calling ChatGPT
        :param temperature: temperature for GPT
        :return: None
        """

        self._prompt_template = prompt_template
        self._temperature = temperature
        self._dialogue_history = ""

        if DIALOG_HISTORY_OLD_TAG in self._prompt_template:
            print(f"Warning: {DIALOG_HISTORY_OLD_TAG} is deprecated. Use {DIALOG_HISTORY_TAG} instead.")


    def generate_next_user_utterance(self, system_utterance: str) -> str:
        """
        generate simulated user utterance following the system utterance
        :param system_utterance: recent system utterance
        :return: generated user utterance
        """

        self._dialogue_history += f'{self._system_name_string}: "{system_utterance}"\n'

        prompt = self._prompt_template.replace(DIALOG_HISTORY_TAG, self._dialogue_history)
        prompt = prompt.replace(DIALOG_HISTORY_OLD_TAG, self._dialogue_history)

        chat_completion = None

        if self._debug:
            print("prompt for generating user utterance: \n" + prompt)

        while True:
            try:
                chat_completion = self._openai_client.with_options(timeout=TIMEOUT).chat.completions.create(
                    model=self._gpt_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    )
            except openai.APITimeoutError:
                continue
            except Exception as e:
                traceback.print_exc()
                raise Exception
            finally:
                if not chat_completion:
                    continue
                else:
                    break
        user_utterance: str = chat_completion.choices[0].message.content
        print(f"generated user utterance: {user_utterance}")
        user_utterance = user_utterance.replace('"','')
        self._dialogue_history += f'{self._user_name_string} "{user_utterance}"\n'

        return user_utterance

    def get_gpt_model(self) -> str:
        """
        returns gpt model name for logging
        :return:
        :rtype:
        """

        return self._gpt_model
