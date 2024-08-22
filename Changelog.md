# Changelog

## 0.9.0 

- LR-CRF Understander Block added

- Sample applications using LR-CRF Understander Block (simple_ja, simple_en) added

- Sample applications using Snips Understander Block (network_ja, network_en) deleted

## 0.8.0

- Change the default environment variable for setting the OpenAI API key to OPENAI_API_KEY.

- STN Manager Builtin Block

  - References to special variables and function calls within system utterances allowed.

  - Builtin generation and conditional functions using LLM (ChatGPT) prepared.

  - Syntactic sugars for embedded scenario functions prepared.

## 0.7.0 (2024.3.6)

- The Japanese experimental application changed so that it uses the ChatGPT language understander.

- The English experimental application added

- ChatGPT Understander Block added

- ChatGPT Dialogue Block changed (not backward compatible)

## 0.6.2 (2024.2.29)

- Bugs in docs fixed

## 0.6.1 (2023.12.22)

- Fixed a bug where the STN Manager block received nlu_result=None

- Supported update of OpenAI library (1.3.5)

## 0.6.0 (2023.8.17)

- Added built-in block for named entity extraction using spaCy/GiNZA
  - Added a usage example to sample_apps/lab_app_ja

- Added ChatGPT built-in block

- Prepared requirements.txt for each sample app

- Renamed dialbb/util/send_test_request.py to dialbb/util/send_test_requests.py

- Made it possible to launch run_server.py from directories other than DIALBB_HOME.

- Integrated the contents of sample_apps/lab_app_ja/README.md into the documentation

## 0.5.1 (2023.8.13)

- STN Manager built-in block

- Fixed a bug where a variable starting with \\# was not returning an empty string when it could not be instantiated

## 0.5.0 (2023.6.29)

- STN Manager built-in block
  - Introduction of subdialogue
  - Introduction of skip state
  - Introduction of request for confirmation utterance
  - Introduction of reactions

## 0.4.0 (2023.6.4)

- In the case of class API, do not modify the request destructively

- Changes in STN Manager built-in block
  - If the value of stop_dialogue in the request's aux_data is True, transition to #final_abort state
  - If the value of "rewind" in the request's "aux_data" is True, revert the dialogue state to the previous one and rewind the dialogue context
  - Changed to optionally select not to transition instead of default transition
  - If the value of "confidence" in the request's "aux_data" is below the "confidence_threshold" value in the configuration's "ask_repetition",
  - In cases where the confidence is below the threshold, do not perform a state transition, and use the utterance value of "ask_repetition" as the system utterance.
  
  - Change the behavior according to the configuration's reaction_to_silence when the input is a long silence
  
  - Implemented built-in scenario functions _confidence_is_low, _is_long_silence
  
  - Allow transition from prep state to a state that is not initial
  
  - Automatically add aux_data to context information
  
  - Add the most recent system utterance to context information
  
  - Fixed a bug where condition function with 0 arguments results in an error
  

## 0.3.0 (2023.4.13)

- Added built-in word segmentation block class. Consequently, the input to SNIPS Understander changed from strings to token sequences (not backward compatible)

## 0.2.1 (2022.12.1)

- Corrected mistakes in the documentation (5.2.2)

## 0.2.0 (2022.12.1)

- Interface changes in AbstractBlock (not backward compatible)
  - Changes to the arguments of the process method
- Set default language to Japanese
- Changes to the STN Manager block
  - Exporting scenario graphs
  - Introduction of preparation state
- Enabled the use of Google Sheets
- Changed the test scenario format (not backward compatible)
- Column name changes for knowledge description for SNIPS Understander (not backward compatible)
- Support for n-best outputs in SNIPS Understander

## 0.1 (2022.8.9)

initial public version
