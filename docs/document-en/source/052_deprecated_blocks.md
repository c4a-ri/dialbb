(builtin_blocks)=
# Deprecated Built-in Block Classes

The following built-in blocks have been deprecated in ver. 2.0.

Even if the DialBB package is installed, the libraries required for these blocks may not be installed.

(simple_canonicalizer)=
## Simple Canonicalizer (Simple String Canonicalizer Block)

(`dialbb.builtin_blocks.preprocess.simple_canonicalizer.SimpleCanonicalizer`)

Canonicalizes user input sentences. The main target language is English.

### Input/Output

- Input
  - `input_text`: Input string (string)
    - Example: "I  like ramen".

- Output
  - `output_text`: string after normalization (string)
    - Example: "i like ramen".

### Process Details

Performs the following processing on the input string.

- Deletes leading and tailing spaces.
- Replaces upper-case alphabetic characters with lower-case characters.
- Deletes line breaks.
- Converts a sequence of spaces into a single space.

(lr_crf_understander)=
## LR-CRF Understander (Language Understanding Block using Logistic Regression and Conditional Random Fields)

(`dialbb.builtin_blocks.understanding_with_lr_crf.lr_crf_understander.Understander`)  

Determines the user utterance type (also called intent) and extracts the slots using logistic regression and conditional random fields.

Performs language understanding in Japanese if the `language` element of the configuration is `ja`, and language understanding in English if it is `en`. 

At startup, this block reads the knowledge for language understanding written in Excel and trains the models for logistic regression and conditional random fields.

At runtime, it uses the trained models for language understanding.


### Input/Output

- input
  - `tokens`: list of tokens (list of strings)
    - Example: `['I' 'like', 'chicken', 'salad' 'sandwiches']`.
  
- output 

  - `nlu_result`: language understanding result (dict or list of dict)
    
	  - If the parameter `num_candidates` of the block configuration described below is 1, the language understanding result is a dictionary type in the following format.
	
	    ```json
	     {
	         "type": <user utterance type (intent)>,. 
	         "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}
	     }
	    ```

	    The following is an example.	  
	  
	    ```json
	     {
	         "type": "tell-like-specific-sandwich", 
	         "slots": {"favorite-sandwich": "roast beef sandwich"}
	     }
	    ```
	  
	  - If `num_candidates` is greater than 1, it is a list of multiple candidate comprehension results.
	  
	    ```json
	     [{"type": <user utterance type (intent)>, 
	       "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}, ...
	      {"type": <user utterance type (intent)>,. 
	       "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}, ...
	      ....]
	    ```

### Block Configuration Parameters

- `knowledge_file` (string)

   Specifies the Excel file that describes the knowledge. The file path must be relative to the directory where the configuration file is located.

- `flags_to_use` (list of strings)

   Specifies the flags to be used. If one of these values is written in the `flag` column of each sheet, it is read. If this parameter is not set, all rows are read.

- `canonicalizer` 

   Specifies the canonicalization information to be performed when converting language comprehension knowledge to Snips training data.

   - `class`
   
      Specifies the class of the normalization block. Basically, the same normalization block used in the application is specified.


- `num_candidates` (integer. Default value is `1`)

   Specifies the maximum number of language understanding results (n for n-best).

- `knowledge_google_sheet` (hash)

  - This specifies information for using Google Sheets instead of Excel.

    - `sheet_id` (string)

      Google Sheet ID.

    - `key_file`(string)

       Specify the key file to access the Google Sheet API as a relative path from the configuration file directory.

(lr_crf_nlu_knowledge)=

### Language Understanding Knowledge

Language understanding knowledge consists of the following two sheets.

| sheet name | contents                                                     |
| ---------- | ------------------------------------------------------------ |
| utterances | examples of utterances by type                               |
| slots      | relationship between slots and entities and a list of synonyms |

The sheet name can be changed in the block configuration, but since it is unlikely to be changed, a detailed explanation is omitted.

#### utterances sheet

Each row consists of the following columns

- `flag`      

  Flags to be used or not. `Y` (yes), `T` (test), etc. are often written. Which flag's rows to use is specified in the configuration. In the configuration of the sample application, all rows are used.


- `type`     

  User utterance type (Intent)        

- `utterance` 

  Example utterance.

- `slots` 

  Slots that are included in the utterance. They are written in the following form

  ```
  <slot name>=<slot value>, <slot name>=<slot value>, ... <slot name>=<slot value> 
  ```

  The following is an example.

  ```
  location=philladelphia, favorite-sandwich=cheesesteak sandwitch
  ```

The sheets that this block uses, including the utterance sheets, can have other columns than these.

#### slots sheet

Each row consists of the following columns.

- `flag`

  Same as on the utterance sheet.

- `slot name` 

  Slot name. It is used in the example utterances in the utterances sheet. Also used in the language understanding results.

- `entity`

  The name of the dictionary entry. It is also included in language understanding results.

- `synonyms`

  Synonyms joined by `','`.



(chatgpt_understander)=
## ChatGPT Understander (Language Understanding Block using ChatGPT)

(`dialbb.builtin_blocks.understanding_with_chatgpt.chatgpt_understander.Understander`)

Determines the user utterance type (also called intent) and extracts the slots using OpenAI's ChatGPT.

Performs language understanding in Japanese if the `language` element of the configuration is `ja`, and language understanding in English if it is `en`. 

At startup, this block reads the knowledge for language understanding written in Excel, and converts it into the list of user utterance types, the list of slots, and the few shot examples to be embedded in the prompt.

At runtime, input utterance is added to the prompt to make ChatGPT perform language understanding.

### Input/Output

- input
  - `input_text`: input string

    The input string is assumed to be canonicalized.

    - Example: `"I like chicken salad sandwiches"`.
  
- output 

  - `nlu_result`: language understanding result (dict)
	
	    ```json
	     {
	         "type": <user utterance type (intent)>,. 
	         "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}
	     }
	    ```

	    The following is an example.	  
	  
	    ```json
	     {
	         "type": "tell-like-specific-sandwich", 
	         "slots": {"favorite-sandwich": "roast beef sandwich"}
	     }
	    ```
	

### Block Configuration Parameters

- `knowledge_file` (string)

   Specifies the Excel file that describes the knowledge. The file path must be relative to the directory where the configuration file is located.

- `flags_to_use` (list of strings)

   Specifies the flags to be used. If one of these values is written in the `flag` column of each sheet, it is read. If this parameter is not set, all rows are read.

- `canonicalizer` 

   Specifies the canonicalization information to be performed when converting language comprehension knowledge to Snips training data.

   - `class`
   
      Specifies the class of the normalization block. Basically, the same normalization block used in the application is specified.


- `knowledge_google_sheet` (hash)

  - This specfies information for using Google Sheet instead of Excel.
  
    - `sheet_id` (string)

      Google Sheet ID.

    - `key_file` (string)

       Specify the key file to access the Google Sheet API as a relative path from the configuration file directory.

- `gpt_model` (string. The default value is `gpt-4o-mini`.)

   Specifies the ChatGPT model. `gpt-4o` can be specified. `gpt-4` cannot be used.

- `prompt_template`

  This specifies the prompt template file as a relative path from the configuration file directory.
  
  When this is not specified, `dialbb.builtin_blocks.understanding_with_chatgpt.prompt_templates_ja .PROMPT_TEMPLATE_JA` (for Japanese) or `dialbb.builtin_blocks.understanding_with_chatgpt.prompt_templates_en .PROMPT_TEMPLATE_EN` (for English) is used.
  
  A prompt template is a template of prompts for making ChatGPT language understanding, and it can contain the following variables starting with `@`.
  
  - `@types` The list of utterance types.
  - `@slot_definitions` The list of slot definitions.
  - `@examples` So-called few shot examples each of which has an utterances example, its utterance type, and its slots. 
  - `@input` input utterance.
  
  Values are assigned to these variables at runtime.

(chatgpt_nlu_knowledge)=
### Language Understanding Knowledge

The description format of the language understanding knowledge in this block is exactly the same as that of the LR-CRF Understander. For more details, please refer to "{ref}`lr_crf_nlu_knowledge`" in the explanation of LR-CRF Understander.


(chatgpt_dialogue)=
## ChatGPT Dialogue (ChatGPT-based Dialogue Block) (Deprecated)

(`dialbb.builtin_blocks.chatgpt.chatgpt.ChatGPT`) 

Engages in dialogue using OpenAI's ChatGPT.

OpenAI社のChatGPTを用いて対話を行います．

LLM Dialogueと同じですが，ChatGPTのモデルしか使えません．コンフィギュレーションのモデル指定のパラメータは`model`ではなく，`gpt_model`です．


(chatgpt_ner)=
## ChatGPT NER (Named Entity Recognition Block Using ChatGPT)

(`dialbb.builtin_blocks.ner_with_chatgpt.chatgpt_ner.NER`)

This block utilizes OpenAI's ChatGPT to perform named entity recognition (NER).

If the `language` element in the configuration is set to `ja`, it extracts named entities in Japanese. If set to `en`, it extracts named entities in English.

At startup, this block reads named entity knowledge from an Excel file, converts it into a list of named entity classes, descriptions for each class, examples of named entities in each class, and extraction examples (few-shot examples), and embeds them into the prompt.

During execution, the input utterance is added to the prompt, and ChatGPT is used for named entity extraction.

### Input and Output

- Input

  - `input_text`: Input string

  - `aux_data`: auxiliary data (dictionary)

- Output

  - `aux_data`: Auxiliary data (dictionary format)

    The named entity extraction results are added to the provided `aux_data`.

    The extracted named entities follow this format:

    ```json
    {"NE_<Label>": "<Named Entity>", "NE_<Label>": "<Named Entity>", ...}
    ```

    `<Label>` represents the named entity class. The named entity is the recognized phrase found in `input_text`. If multiple entities of the same class are found, they are concatenated with `:`.

    Example:

    ```json
    {"NE_Person": "John:Mary", "NE_Dish": "Chicken Marsala"}
    ```

### Block Configuration Parameters

- `knowledge_file` (String)  

  Specifies the Excel file containing named entity knowledge. The file path should be relative to the directory where the configuration file is located.

- `flags_to_use` (List of strings)  

  If any of these values are present in the `flag` column of each sheet, the corresponding row will be loaded. If this parameter is not set, all rows will be loaded.

- `knowledge_google_sheet` (Hash)  

  Information for using Google Sheets instead of Excel. 

  - `sheet_id` (String)  

    The ID of the Google Sheet.

  - `key_file` (String)  

    Specifies the key file for accessing the Google Sheet API. The file path should be relative to the configuration file directory.

- `gpt_model` (String, default: `gpt-4o-mini`)  

  Specifies the ChatGPT model. Options include `gpt-4o`, etc.

- `prompt_template`

  Specifies the file containing the prompt template, relative to the configuration file directory.

  If not specified, the default templates `dialbb.builtin_blocks.ner_with_chatgpt.chatgpt_ner.prompt_template_ja.PROMPT_TEMPLATE_JA` (for Japanese) or `dialbb.builtin_blocks.ner_with_chatgpt.chatgpt_ner.prompt_template_en.PROMPT_TEMPLATE_EN` (for English) will be used.

  The prompt template defines how ChatGPT is instructed for language understanding and includes the following variables (prefixed with `@`):

  - `@classes` List of named entity classes.

  - `@class_explanations` Descriptions of each named entity class.

  - `@ne_examples` Examples of named entities for each class.

  - `@ner_examples` Examples of utterances and their correct named entity extraction results (few-shot examples).

  - `@input` The input utterance.

  Values are assigned to these variables at runtime.

### Named Entity Knowledge

Named entity knowledge consists of the following two sheets:

| Sheet Name  | Description |
| ----------- | ----------- |
| utterances  | Examples of utterances and named entity extraction results. |
| classes     | Relationship between slots and entities, along with a list of synonyms. |

Although the sheet names can be changed in the block configuration, this is rarely needed, so detailed explanations are omitted.

#### utterances Sheet

Each row consists of the following columns:

- `flag`

  A flag to determine whether to use the row. Common values include `Y` (yes) and `T` (test). The configuration specifies which flags to use.

- `utterance`

  Example utterance.

- `entities`

  Named entities contained in the utterance. They are formatted as follows:

  ```
  <Named Entity Class>=<Named Entity>, <Named Entity Class>=<Named Entity>, ... <Named Entity Class>=<Named Entity>
  ```

  Example:

  ```
  Person=John, Location=Chicago
  ```

  Additional columns besides these are allowed in the sheets used by this block.

#### classes Sheet

Each row consists of the following columns:

- `flag`

  Same as in the `utterances` sheet.

- `class`

  Named entity class name.

- `explanation`

  Description of the named entity class.

- `examples`

  Examples of named entities, concatenated with `','`.

(spacy_ner)=
## spaCy-Based NER (Named Entity Recognizer Block using spaCy)
(`dialbb.builtin_blocks.ner_with_spacy.ne_recognizer.SpaCyNER`)

Performs named entity recognition using [spaCy](https://spacy.io) and [GiNZA](https://megagonlabs.github.io/ginza/).

### Input/Output

- Input

  - `input_text`: Input string (string)

  - `aux_data`: auxiliary data (dictionary)
  
- Output

  - `aux_data`: auxiliary data (dictionary)
    
     The inputted `aux_data` plus the named entity recognition results.

The result of named entity recognition is as follows.

```json
{ 
  "NE_<label>": "<named entity>", 
  "NE_<label>": "<named entity>", 
  ...
}
```

`<label>` is the class of named entities. `<named entity>` is a found named entity, a substring of ``input_text`. If multiple named entities of the same class are found, they are concatenated with `':'`.

Example:
	 
```json
{ 
  "NE_Person": "John:Mary", 
  "NE_Dish": "Chiken Marsala"
}
```

See the spaCy/GiNZA model website for more information on the class of named entities.
	 
 - `ja-ginza-electra` (5.1.2): [https://pypi.org/project/ja-ginza-electra/](https://pypi.org/project/ja-ginza-electra/) 
 - `en_core_web_trf` (3.5.0): [https://spacy.io/models/en#en_core_web_trf-labels](https://huggingface.co/spacy/en_core_web_trfhttps://pypi.org/project/ja-ginza-electra/)

 

### Block Configuration Parameters

- `model` (String: Required)

   The name of the spaCy/GiNZA model. It can be `ja_ginza_electra` (Japanese), `en_core_web_trf` (English), etc.

- `patterns` (object; Optional)

   Describes a rule-based named entity extraction pattern. The pattern is a YAML format of the one described in [spaCy Pattern Description](https://spacy.io/usage/rule-based-matching).

   
   The following is an example.
   
   ```yaml
   patterns: 
     - label: Date
       pattern: yesterday
     - label: Date
       pattern: The day before yesterday
   ```

### Process Details

Extracts the named entities in `input_text` using spaCy/GiNZA and returns the result in `aux_data`.

