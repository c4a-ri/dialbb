import os, sys
import traceback

import openai
import google.generativeai as genai
from typing import Dict, Any

DEFAULT_GPT_MODEL: str = "gpt-4o-mini"
DIALOG_HISTORY_TAG: str = '{dialogue_history}'
DIALOG_HISTORY_OLD_TAG: str = '@dialogue_history'
TIMEOUT: int = 10

class LLMTester:

    def __init__(self, test_config: Dict[str, Any]):

        self._debug = False
        if os.environ.get('DIALBB_TESTER_DEBUG', 'no').lower() == "yes":
            self._debug = True

        self._llm_type = test_config.get("llm_type", "chatgpt")
        self._llm = test_config.get("model", "")

        if self._llm_type == "chatgpt":

            openai_key: str = os.environ.get('OPENAI_KEY', os.environ.get('OPENAI_API_KEY', ""))
            if not openai_key:
                print("environment variable OPENAI_KEY or OPENAI_API_KEY is not defined.")
                sys.exit(1)
            self._openai_client = openai.OpenAI(api_key=openai_key)
            openai.api_key = openai_key
            self._gpt_model: str = test_config.get("model", DEFAULT_GPT_MODEL)

        elif self._llm_type == "gemini":

            google_api_key: str = os.environ.get('GOOGLE_API_KEY')
            if not google_api_key:
                print("environment variable GOOGLE_API_KEY is not defined.")
                sys.exit(1)
            genai.configure(api_key=google_api_key)
            self._gemini_model = genai.GenerativeModel(self._llm)

        else:

            print("unsupported llm type: " + self._llm_type)
            sys.exit(1)

        self._prompt_template: str = ""
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



        if self._debug:
            print("prompt for generating user utterance: \n" + prompt)

        if self._llm_type == 'chatgpt':

            chat_completion = None
            while True:
                try:
                    chat_completion = self._openai_client.with_options(timeout=TIMEOUT).chat.completions.create(
                        model=self._gpt_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self._temperature,
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

        elif self._llm_type == 'gemini':

            response = None
            while True:
                try:
                    gemini_config = genai.types.GenerationConfig(temperature=self._temperature)
                    response = self._gemini_model.generate_content(prompt, generation_config=gemini_config)
                except genai.errors.APIError as e:
                    if hasattr(e, "code") and e.code in [429, 500, 503]:
                        print (f"Gemini error with code {str(e.code)}. Repeating.")
                        continue
                except Exception:
                    traceback.print_exc()
                    raise Exception
                finally:
                    if not response:
                        print (f"No response from Gemini. Repeating.")
                        continue
                    else:
                        break
            user_utterance: str = response.text.strip()

        print(f"generated user utterance: {user_utterance}")
        user_utterance = user_utterance.replace('"','')
        self._dialogue_history += f'{self._user_name_string} "{user_utterance}"\n'

        return user_utterance

    def get_llm_model(self) -> str:
        """
        returns gpt model name for logging
        :return:
        :rtype:
        """

        return self._llm
