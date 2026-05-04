(builtin_blocks)=
# Built-in Block Classes

Built-in block classes are block classes that are included in DialBB in advance.

(chatgpt_understander)=
## LLM with DST (DST Block using an LLM)

(`dialbb.builtin_blocks.understanding_with_chatgpt.chatgpt_understander.Understander`)

This uses a large language model to perform slot extraction from dialogue history, namely Dialogue State Tracking (DST).

It performs DST in Japanese if the `language` element of the configuration is `ja`, and language understanding in English if it is `en`. 

At startup, this block reads the knowledge for DST in Excel, and converts it into the list of slots, and the few shot examples to be embedded in the prompt.

At runtime, the dialogue history is added to the prompt to make an LLM perform DST.

### Input/Output

- input

  - `dialogue_history`: dialogue history

    This is the dialogue history retained by the main module.
  
- output 

  - `nlu_result`: language understanding result (dict)
	
	    ```json
	     {
	       <slot name>: <slot value>, 
		   ... , 
		   <slot name>: <slot value>
	     }
	    ```

	    The following is an example.	  
	  
	    ```json
	     {
	       "user-name": "John",
	       "favorite-sandwich": "roast beef sandwich"
	     }
	    ```
	

### Block Configuration Parameters

- `knowledge_file` (string)

   Specifies the Excel file that describes the knowledge. The file path must be relative to the directory where the configuration file is located.

- `flags_to_use` (list of strings)

   Specifies the flags to be used. If one of these values is written in the `flag` column of each sheet, it is read. If this parameter is not set, all rows are read.

- `knowledge_google_sheet` (hash)

  - This specfies information for using Google Sheet instead of Excel.
  
    - `sheet_id` (string)

      Google Sheet ID.

    - `key_file` (string)

       Specify the key file to access the Google Sheet API as a relative path from the configuration file directory.

- `model` (string. The default value is `gpt-4o-mini`.)

   Specifies the LLM. 

- `prompt_template`

  This specifies the prompt template file as a relative path from the configuration file directory.
  
  When this is not specified, `dialbb.builtin_blocks.dst_with_llm.prompt_templates_ja .PROMPT_TEMPLATE_JA` (for Japanese) or `dialbb.builtin_blocks.dst_with_llm.prompt_templates_en .PROMPT_TEMPLATE_EN` (for English) is used.
  
  A prompt template is a template of prompts for making the LLM extract slots, and it can contain the following place holders.
  
  - `{slot_definitions}` The list of slot definitions.
  - `{examples}` So-called few shot examples each of which has an utterances example, its utterance type, and its slots. 
  - `{dialogue_history}` input utterance.
  
  Values are assigned to these variables at runtime.

### DST Knowledge

DST knowledge consists of the following two sheets.

| sheet name | contents                                                     |
| ---------- | ------------------------------------------------------------ |
| dialogues  | examples of dialogues and slot extraction results                  |
| slots      | relationship between slots and entities and a list of synonyms |

The sheet name can be changed in the block configuration, but since it is unlikely to be changed, a detailed explanation is omitted.

#### utterances sheet

Each row consists of the following columns

- `flag`      

  Flags to be used or not. `Y` (yes), `T` (test), etc. are often written. Which flag's rows to use is specified in the configuration. In the configuration of the sample application, all rows are used.


- `dialogue` 

  Example dialogue.

  The following is an example:
  
  ```
  System: Can I have your name?
  User: Linda. Nice to meet you.
  System: Nice to meet you, too. Let's talk about food. Do you like sandwiches?
  User: Yes, I like roast beef sandwiches
  ```

- `slots` 

  Slots that should be extracte from the dialogue. They are written in the following form:

  ```
  <slot name>=<slot value>, <slot name>=<slot value>, ... <slot name>=<slot value> 
  ```

  The following is an example.

  ```
  user_name=Linda, favorite_sandwich=roast beef sandwiches

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


(stn_manager)=
## STN Manager (State Transition Network-based Dialogue Management Block)

(`dialbb.builtin_blocks.stn_manager.stn_management`)  

It perfomrs dialogue management using a state-transition neetwork.

- input
  - `sentence`: user utterance after canonicalization (string)

  - `nlu_result`: language understanding result (dictionary or list of dictionaries)

  - `user_id`: user ID (string)

  - `aux_data`: auxiliary data (dictionary) (not required, but specifying this is recommended)


- output 

  - `output_text`: system utterance (string)

     Example:

	```
	"So you like chiken salad sandwiches."
	```

  - `final`: a flag indicating whether the dialog is finished or not. (bool)

  - `aux_data`: auxiliary data (dictionary type) 

     The auxiliary data of the input is updated in action functions described below, including the ID of the transitioned state. Updates are not necessarily performed in action functions. The transitioned state is added in the following format.

    ```json
	  {"state": "I like a particular ramen" }
    ```
    
### Block configuration parameters

- `knowledge_file` (string)

  Specifies an Excel file describing the scenario. It is a relative path from the directory wherer  the configuration file exists.

- `function_definitions` (string)

  The name of the module that defines the scenario function (see {ref}`dictionary_function`). If there are multiple modules, connect them with `':'`. The module must be in the Python module search path. (The directory containing the configuration file is in the module search path.)

- `flags_to_use` (list of strings)

  Same as the Snips Understander.

- `knowledge_google_sheet` (object)

  Same as the Snips Understander.

- `scenario_graph`: (boolean. Default value is `False`)

   If this value is `true`, the values in the `system utterance` and `user utterance example` columns of the scenario sheet are used to create the graph. This allows the scenario writer to intuitively see the state transition network.

- `repeat_when_no_available_transitions` (Boolean. Default value is `false`)

   When this value is `true`, if there is no transition that matches the condition, the same utterance is repeated without transition.

- `multi_party` (Boolean. Deafault value is `false`)

   When this value is set to `true`, the value of `user_id` is included in the conversation history for {numref}`context_information` and in the prompts for built-in functions using large language models described in {numref}`llm_functions`.


(scenario)=
### Dialogue Management Knowledge Description

The dialog management knowledge (scenario) is written in the scenario sheet in the Excel file.

Each row of the sheet represents a transition. Each row consists of the following columns

- `flag`

  Same as on the utterances sheet.

- `state`

  The name of the source state of the transition.

- `system utterance`

    Candidates of the system utterance generated in the `state` state. 
	
	The `{<variable>}` or `{<function call>}` in the system utterance string is replaced by the value assigned to the variable during the dialogue or the return value of the function call. This will be explained in detail in "{ref}`realization_in_system_utterance`".
	
	There can be multiple lines with the same `state`, but all `system utterance` in the lines having the same `state` become system utterance candidates, and will be chosen randomely.

- `user utterance example`

  Example of user utterance. It is only written to understand the flow of the dialogue, and is not used by the system.

- `user utterance type`

  The user utterance type obtained by language understanding. It is used as a condition of the transition.


- `conditions`

  Condition (sequence of conditions). A function call that represents a condition for a transition. There can be more than one. If there are multiple conditions, they are concatenated with `';'`. Each condition has the form `<function name>(<argument 1>, <argument 2>, ..., <argument n>)`. The number of arguments can be zero. See {ref}`arguments` for the arguments that can be used in each condition.

- `actions`

  A sequece of actions, which are function calls to execute when the transition occurs. If there is more than one, they are concatenated with `;`. Each condition has the form `<function name>(<argument 1>, <argument 2>, ..., <argument n>)`. The number of arguments can be zero. See {ref}`arguments` for the arguments that can be used in each condition.


- `next state`

  The name of the destination state of the transition.

There can be other columns on this sheet (for use as notes).

If the `user utterance type` of the transition represented by each line is empty or matches the result of language understanding, and if the `conditions` are empty or all of them are satisfied, the condition for the transition is satisfied and the transition is made to the `next state` state. In this case, the action described in `actions` is executed.


Rows with the same `state` column (transitions with the same source state) are checked to see if they satisfy the transition conditions, **starting with the one written above**.

The default transition (a line with both `user utterance type` and `conditions` columns empty) must be at the bottom of the rows having the `state` column values.

Unless `repeat_when_no_available_transitions` is `True`, the default transition is necessary.


### Special status

The following state names are predefined.

- `#prep`

  Preparation state. If this state exists, a transition from this state is attempted when the dialogue begins (when the client first accesses). The system checks if all conditions in the conditions column of the row with the `#prep` value in the `state` column are met. If they are, the actions in that row's actions are executed, then the system transitions to the state in next state, and the system utterance for that state is outputted.

  This is used to change the initial system utterance and state according to the situation. The Japanese sample application changes the content of the greeting depending on the time of the day when the dialogue takes place.

  This state is not necessary.

- `#initial`

  Initial state. If there is no `#prep state`, the dialogue starts from this state when it begins (when the client first accesses). The system utterance for this state is placed in `output_text` and returned to the main process. 

  There must be either `#prep` or `#initial` state.

- `#error`

  Moves to this state when an internal error occurs. Generates a system utterance and exits.


  A state ID beginning with `#final`, such as `#final_say_bye`, indicates a final state.
In a final state, the system generates a system utterance and terminates the dialog.

### Conditions and Actions

(context_information)=
#### Context information

STN Manager maintains context information for each dialogue session. The context information is a set of variables and their values (python dictionary type data), and the values can be any data structure.


Condition and action functions access context information.


The context information is pre-set with the following key-value pairs.

| key | value |
| ------------- | ------------------------------------------------------------ |
| _current_state_name | name of the state before transition (string)|
| _config | dictionary type data created by reading configuration file |
| _block_config | The part of the dialog management block in the configuration file (dictionary) |
| _aux_data | aux_data (dictionary) received from main process|
| _previous_system_utterance | previous system utterance (string)|
| _dialogue_history | Dialogue history (list)|
| _turns_in_state | The number of user turns in the current state (integer)|
| _session_id | The session ID of the current conversation (string) |
| _user_id | The user ID of the most recent user utterance (string) |

The dialog history is in the following form.

```python
[
  {
    "speaker": "user",
    "utterance": <canonicalized user utterance (string)>
  },
  {
    "speaker": "system",
    "utterance": <canonicalized user utterance (string)
  },
  {
    "speaker": "user",
    "utterance": <canonicalized user utterance (string)
  },
  ...
]
```

In addition to these, new key/value pairs can be added within the action function.

(arguments)=
#### Function arguments

The arguments of the functions used in conditions and actions are of the following types.


- Special variables (strings beginning with `#`)

  The following types are available

  - `#<slot name>`

    Slot value of the  language understanding result of the previous user utterance (the input `nlu_result` value). If the slot value is empty, it is an empty string.

  - `#<key for auxiliary data>`
    
    The value of this key in the input `aux_data`. For example, in the case of `#emotion`, the value of `aux_data['emotion']`. If this key is missing, it is an empty string.


  - `#sentence` 
  
    Immediate previous user utterance (canonicalized)
    
  - `#user_id` 
  
    User ID string


- Variables (strings beginning with `*`)

  The value of a variable in context information. It is in the form `*<variable name>`. The value of a variable must be a string. If the variable is not in the context information, it is an empty string.

- Variable reference (string beginning with `&`)

  Refers to a context variable in function definitions. It is in the form `&<context variable name>` 

- Constant (string enclosed in `""`)

  It means the string as it is.


(realization_in_system_utterance)=
### Variables and Function Calls in System Utterances

In system utterances, parts enclosed in `{` and `}` are variables or function calls that are replaced by the value of the variable or the return value of the function call.

Variables that start with `#` are special variables mentioned above. Other variables are normal variables, which are supposed to be present in the context information. If these variables do not exist, the variable names are used as is without replacement.

For function calls, the functions can take arguments explained above as functions used for conditions or actions. The return value must be a string.

### Function Definitions

Functions used in conditions and actions (called "scenario functions" altogether)are either built-in to DialBB or defined by the developers. The function used in a condition returns a Boolean value, while the function used in an action returns nothing.


#### Built-in functions

The built-in functions are as follows:

- Functions used in conditions

  - `_eq(x, y)`

    Returns `True` if `x` and `y` are the same.

    e.g.,  `_eq(*a, "b")` returns `True` if the value of variable `a` is `"b"`.
    `_eq(#food, "sandwich")`: returns `True` if `#food` slot value is `"sandwich"`.

  - `_ne(x, y)`

    Returns `True` if `x` and `y` are not the same.

    e.g., `_ne(#food, "ramen")` returns `False` if `#food` slot is `"ramen"`.

  - `_contains(x, y)`

    Returns `True` if `x` contains `y` as a string.

    e.g.,  `contains(#sentence, "yes")` : returns `True` if the user utterance contains "yes".

  - `_not_contains(x, y)`

    Returns `True` if `x` does not contain `y` as a string.

    e.g.,  `_not_contains(#sentence, "yes")`  returns `True` if the user utterance contains `"yes"`.
    
  - `_member_of(x, y)`

    Returns `True` if the list formed by splitting `y` by `':'` contains the string `x`.

    e.g., `_member_of(#food, "ramen:fried rice:dumplings")`


  - `_not_member_of(x, y)`

    e.g., `_not_member_of(*favorite_food, "ramen:fried_han:dumpling")`
    
  - `_num_turns_exceeds(n)`
  
	Returns `True` when the number of user turns exceeds the integer represented by the string `n`. 
	
    e.g.: `_num_turns_exceeds("10")`

  - `_num_turns_in_state_exceeds(n)`
  
	Returns `True` when the number of user turns in the current state exceeds the integer represented by the string `n`. 
	
    e.g.: `_num_turns_in_state_exceeds("5")`

  - `_check_with_llm(task)` and `_check_with_prompt_template(prompt_template)`
  
     Makes the judgment using a large language model. More details follow.


- Functions used in actions

  - `_set(x, y)`

    Sets `y` to the variable `x`.

    e.g.,  `_set(&a, b)`: sets the value of `b` to `a`.

    `_set(&a, "hello")`: sets `"hello"` to `a`.


  - `_set(x, y)`

    Sets `y` to the variable `x`.

    e.g., `_set(&a, b)`: sets the value of `b` to `a`. 

    `_set(&a, "hello")`: sets `"hello"` to `a`.

- Functions used in system utterances

  - `_generate_with_llm(task)` and `_generate_with_prompt_template(prompt_template)`
  
     Generates a string using a large language model (currently only OpenAI's ChatGPT). More details follow.


(llm_functinos)=
#### Built-in functions using large language models

The functions `_check_with_llm(task)` and `_generate_with_llm(task)` use a large language model (currently only OpenAI's ChatGPT) along with dialogue history to perform condition checks and text generation. Here are some examples:


- Example of a condition check:

  ```python
  _check_with_llm("Please determine if the user said the reason.")
  ```

- Example of text generation:

  ```python
  _generate_with_llm("Generate a sentence to say it's time to end the talk by continuing the conversation in 50 words.")
  ```

To use these functions, the following settings are required:

  
- Add the following elements to the `llm` element (`chatgpt` element is possible but deprecated) in the block configuration:

  - `model` (string) (`gpt_model` can also be used but deprecated.)

    This specifies model.

  - `instruction` (string)

    This is used as the system role message when calling the ChatGPT API. It is only used during text generation. See [this](https://github.com/c4a-ri/dialbb/blob/main/dialbb/util/globals.py)default for the default value.

  - `temperature` (float)

    This specifies the temperature parameter for GPT. The default value is `0.7`.

  - `temperature_for_checking` (float)

    This is the temperature parameter of the GPT used during conditional evaluation. If this is not specified, the value of `temperature` will be used instead.

  - `situation` (list of strings)

    A list that enumerates the scenarios to be written in the GPT prompt. If this element is absent, no specific situation is specified.


  - `persona` (lis of strings)

    A list that enumerates the system persona to be written in the GPT prompt.

    If this element is absent, no specific persona is specified.


  - `cautions` (list of strings)

    A list of cautionary notes or warnings intended for the system to be written in the GPT prompt.

    If this element is not present, no cautions are specified.

    In the case of `check_with_llm`, even if this element exists, the cautions are not specified.



  e.g.:

  ```yaml
    chatgpt:
      gpt_model: gpt-4-turbo
      temperature: 0.7
      situation:
        - You are a dialogue system and chatting with the user.
        - You met the user for the first time.
        - You and the user are similar in age.
        - You and the user talk in a friendly manner.
      persona:
        - Your name is Yui
        - 28 years old
        - Female
        - You like sweets
        - You don't drink alcohol
        - A web designer working for an IT company
        - Single
        - You talk very friendly
        - Diplomatic and cheerful
      cautions:
        - Do not generate long sentences
        - Do not put period at the end of sentences
  ```

`_check_with_prompt_template(prompt_template)` and `_generate_with_llm(prompt_template)` perform condition checking and text generation by providing prompts to a large language model.
The prompts are created by replacing the placeholders in the specified prompt template with actual values.

To use these functions, you must set the environment variable `OPENAI_API_KEY` and configure the `chatgpt` element in the block configuration.

Here are some examples:

- Example of condition checking:

  ```python
  _check_with_llm("Please determine whether the user has given a reason.")
  ```

- Another example of condition checking:

  ```python
  _generate_with_prompt_template("""

  # Situation

  {situation}

  # Your persona

  {persona}

  # Cautions

  {cautions}

  # Dialogue history up to now

  {dialogue_history}

  # Task

  Determine whether the user has given a reason, and answer with either 'yes' or 'no'.
  """)
  ```

- Example of string generation:

  ```python
  _generate_with_prompt_template("""

  # Situation

  {situation}

  # Your persona

  {persona}

  # Cautions

  {cautions}

  # Dialogue history up to now

  {dialogue_history}

  # Task

  Based on the dialogue so far, generate a closing utterance within 50 characters.
  """)
  ```

  Parts enclosed in `{` and `}` are placeholders.

- Available placeholders:

  - `{dialogue_history}`
    Replaced with the dialogue up to that point, including the latest user utterance.

  - `{situation}`
    Replaced with the value of `situation` from the `chatgpt` element in the block configuration.

  - `{persona}`
    Replaced with the value of `persona` from the `chatgpt` element in the block configuration.

  - `{cautions}`
    Replaced with the value of `cautions` from the `chatgpt` element in the block configuration.

  - `{current_time}`
    Replaced with a string representing the current date, day of the week, and time (hour, minute, second) at which the dialogue is taking place.


  - `{<a string consisting only of alphabets, digits, and underscores>}`

     If the string exists as a key in aux_data, it is replaced with the corresponding value converted to a string.
	
- Placeholder removal

  If an unreplaced placeholder remains and is enclosed in `[[[` and `]]]`, that portion will be removed.


#### Syntax sugars for built-in functions

Syntax sugars are provided to simplify the description of built-in functions.


- `<variable name>==<value>`

  This means `_eq(<variable name>, <value>)`.

  e.g.:

  ```
  #favorite_sandwich=="chiken salad sandwich"
  ```

- `<variable name>!=<value>`

  This means `_ne(<variable name>, <value>)`.

  e.g.:

  ```
  #NE_Person!=""
  ```

- `<variable name>=<value>`

  This means `_set(&<variable name>, <value>)`.

  e.g.:

  ```
  user_name=#NE_Person
  ```

- `TT > <integer>`

  This means `_num_turns_exceeds("<integer>")`.

  e.g.:

  ```
  TT>10
  ```

- `TS > <integer>`

  This means `_num_turns_in_state_exceeds("<integer>")`.

  e.g.:

  ```
  TS>5
  ```

- `$<task string>$`

  When used as a condition, it means `_check_with_llm("<task string>")`, and when used in a system utterance, it means `{_generate_with_llm("<task string>")}`.

  Example of a condition:

  ```
  $Please determine if the user said the reason$
  ```

  Example of a text generation function call in a system utterance:
  
  ```
  I understand. $Generate a sentence to say it's time to end the talk by continuing the conversation in 50 words$  Thank you for your time.

  ```

  This used to be `$"<task string>"` but it is deprecated.

- `$$$<prompt template>$$$`

  When used as a condition, it means `_check_with_prompt_template("<prompt template>")`, and when used in system utterances, it means `{_generate_with_prompt_template("<prompt template>")}`.


(custom_functions)=
#### Function definitions by the developers

When the developer defines functions, he/she edits a file specified in `function_definition` element in the block configuration.

```python
def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None: 
    location:str = ramen_map.get(ramen, "Japan")
    context[variable] = location
```

In addition to the arguments used in the scenario, variable of dictionary type must be added to receive context information.

All arguments used in the scenario must be strings.
In the case of a special variable or variables, the value of the variable is passed as an argument.
In the case of a variable reference, the variable name without the `&`' is passed, and in the case of a constant, the string in `""` is passed.

#### Logging in functions

In scenario functions, logging can be performed using the following functions. The logs are written to standard output along with the session ID.

- `dialbb.builtin_blocks.stn_management.util.scenario_function_log_debug(message: str)`
   Writes a log at the debug level.
- `dialbb.builtin_blocks.stn_management.util.scenario_function_log_info(message: str)`
   Writes a log at the info level.
- `dialbb.builtin_blocks.stn_management.util.scenario_function_log_warning(message: str)`
   Writes a log at the warning level.
- `dialbb.builtin_blocks.stn_management.util.scenario_function_log_error(message: str)`
   Writes a log at the error level. In debug mode, this function also raises an Exception.

### Reaction

In an action function, setting a string to `_reaction` in the context information will prepend that string to the system's response after the state transition.

For example, if the action function `_set(&_reaction, "I agree.")` is executed and the system's response in the subsequent state is "How was the food?", then the system will return the response "I agree. How was the food?".

(extract_aux_data)=

### Extraction of aux_data from System Utterances

When the output system utterance string ends with a segment in the format `(<key_1>: <value_1>,  <key_2>: <value_2>, ... <key_n>: <value_n>)`, this part is removed from the utterance string, and the corresponding data is added to the output’s `aux_data` as: `{"<key_1>": "<value_1>",  "<key_2>": "<value_2>", ... "<key_n>": "<value_n>"} (If a key already exists, the value is updated.) This mechanism can be used for client-side control.

Example:

- System utterance string: `"Hello! (emotion:happy)"`
- Final system utterance: `"Hello"`,  Update to `aux_data`: `{"emotion": "happy"}`

Each key must consist of a combination of letters, numbers, and underscores.

### Continuous Transition

If a transition is made to a state where the first system utterance is `$skip`, the next transition is made immediately without returning a system response. This is used in cases where the second transition is selected based on the result of the action of the first transition.

### Dealing with Multiple Language Understanding Results

If the input `nlu_result` is a list that contains multiple language understanding results, the process is as follows.

Starting from the top of the list, check whether the `type` value of a candidate language understanding result is equal to the `user utterance type` value of one of the possible transitions from the current state, and use the candidate language understanding result if there is an equal transition. If none of the candidate language comprehension results meet the above conditions, the first language comprehension result in the list is used.

### Subdialogue

If the destination state name is of the form `#gosub:<state name1>:<state name2>`, it transitions to the state `<state name1>` and executes a subdialogue starting there. If the destination state is `:exit`, it moves to the state `<state name2>`.
For example, if the destination state name is of the form `#gosub:request_confirmation:confirmed`, a subdialogue starting with `request_confirmatin` is executed, and when the destination state becomes `:exit`, it returns to `confirmed`. When the destination becomes `:exit`, it returns to `confirmed`.
It is also possible to transition to a subdialogue within a subdialogue.

### Saving Context Information in an External Database

When the configuration includes a `context_db` element, contextual information is stored in an external database (MongoDB). For details on how to specify `context_db`, please refer to {numref}`context_db`.

(In version 1.2, `context_db` was changed to be specified at the top level of the configuration rather than in the block configuration.)

### Advanced Mechanisms for Handling Speech Input

#### Additional block configuration parameters

- `input_confidence_threshold` (float; default value `1.0`)
   If the input is a speech recognition result and its confidence is less than this value, the confidence is considered low. The confidence of the input is the value of `confidence` in `aux_data`. If there is no `confidence` key in `aux_data`, the confidence is considered high. In the case of low confidence, the process depends on the value of the parameter described below.

- `confirmation_request` (object)

   This is specified in the following form.

   ```yaml
   confirmation_request:
     function_to_generate_utterance: <function name (string)>
     acknowledgement_utterance_type: <user utterance type name of acknowledgement (string)>
     denial_utterance_type: <name of user utterance type for affirmation (string)>
   ```

   If this is specified, the function specified in `function_to_generate_utterance` is executed and the return value is spoken (called a confirmation request utterance), instead of making a state transition when the input is less certain.
   Then, the next process is performed in response to the user's utterance.

   - When the confidence level of the user's utterance is low, the transition is not made and the previous state of utterance is repeated.


   - If the type of user utterance is specified by `acknowledgement_utterance_type`, the transition is made according to the user utterance before the acknowledgement request utterance.

   - If the type of user utterance is specified by `denial_utterance_type`, no transition is made and the utterance in the original state is repeated.


   - If the user utterance type is other than that, a normal transition is performed.


   However, if the input is a barge-in utterance (`aux_data` has a `barge_in` element and its value is `True`), this process is not performed.

   The function specified by `function_to_generate_utterance` is defined in the module specified by `function_definitions` in the block configuration. The arguments of the function are the `nlu_result` and context information of the block's input. The return value is a string of the system utterance.    

- `utterance_to_ask_repetition` (string)

   If it is specified, then when the input confidence is low, no state transition is made and the value of this element is taken as the system utterance. However, in the case of barge-in (`aux_data` has a `barge_in` element and its value is `True`), this process is not performed.

   

   `confirmation_request` and `utterance_to_ask_repetition` cannot be specified at the same time.
   
- `ignore_out_of_context_barge_in` (Boolean; default value is `False`). 

  If this value is `True`, the input is a barge-in utterance (the value of `barge_in` in the `aux_data` of the request is `True`), the conditions for a transition other than the default transition are not met (i.e. the input is not expected in the scenario), or the confidence level of the input is low the transition is not made. In this case, the `barge_in_ignored` of the response `aux_data` is set to `True`.


- `reaction_to_silence` (object)

   It has an `action` element. The value of the `action` element is a string that can be either `repeat` or `transition`. If the value of the `action` element is `"transition"`, the `"destination"` element is required. The value of the `destination` key is a string.

   If the input `aux_data` has a `long_silence` key and its value is `True`, and if the conditions for a transition other than the default transition are not met, then it behaves as follows, depending on this parameter:
   
   - If this parameter is not specified, normal state transitions are performed.
   
   
   - If the value of `action` is `"repeat"`, the previous system utterance is repeated without state transition.
   
   
   - If the value of `action` is `"transition"`, then the transition is made to the state specified by `destination`.

#### Adding built-in condition functions

The following built-in condition functions have been added

-  `_confidence_is_low()` 

   Returns `True` if the value of `confidence` in the   input `aux_data` is less than or equal to the value of `input_confidence_threshold` in the configuration.

-  `_is_long_silence()`

    Returns `True` if the value of `long_silence` in the input's `aux_data` is `True`.

#### Ignoring the last incorrect input

If the value of `rewind` in the input `aux_data` is `True`, a transition is made from the state before the last response.
Any changes to the dialog context due to actions taken during the previous response will also be undone.
This function is used when a user utterance is accidentally split in the middle during speech recognition and only the first half of the utterance is responded to.

Note that the context information is reverted, but not if you have changed the value of a global variable in an action function or the contents of an external database.

(chatgpt_dialogue)=
## LLM Dialogue (LLM-based Dialogue Block)

(`dialbb.builtin_blocks.llm_dialogue.llm_dialogue.LLMDialogue`)

Engages in dialogue using an LLM (Large Language Model).

### Input/Output

- Input

  - `user_utterance`: Input string (string)
  - `aux_data`: Auxiliary data (dictionary).
  - `user_id`: User ID (string)
  - `dialogue_history`: Dialogue history (list of dictionaries)

- Output

  - `system_utterance`: Input string (string)
  - `aux_data`: auxiliary data (dictionary type)
  - `final`: Boolean flag indicating whether the dialog is finished or not.

The input `user_id` is not used. The output `aux_data` is the same as the input `aux_data` and `final` is always `False`.

When using these blocks, you need to set the OpenAI license key in the environment variable `OPENAI_API_KEY`.

### Block Configuration Parameters

- `first_system_utterance` (string, default value is `""`)

   This is the first system utterance of the dialog.

- `user_name` (string, default value is `"User"`.)

   This string is used when providing conversation history to the LLM prompt.

- `system_name` (string, default value is "System")

   This string is used when providing conversation history to the LLM prompt.

- `prompt_template` (string)

  This specifies the file of the prompt for making LLM generate a system utterance as a relative path from the configuration file directory.

- `temperature` (float, default value is `0.7`)

  The temperature parameter when calling LLM.

- `model` (string, default value is `gpt-4o-mini`)

   Model specifier. Use `provider:model_name` such as `google_genai:gemini-2.0-flash-001`. OpenAI GPT models such as `gpt-4o` and `gpt-4o-mini` may omit the `openai:` prefix.

- `instruction` (string, see [this](https://github.com/c4a-ri/dialbb/blob/main/dialbb/util/globals.py)default for the default value.)

   The instruction to LLM as system role message.


### Place Holders in Prompt Templates

- The following place holders can be used in prompt templates.

  - `{current_time}`
    Replaced with a string representing the current date, day of the week, and time (hour, minute, second) at which the dialogue is taking place.

  - `{<a string consisting only of alphabets, digits, and underscores>}`

     If the string exists as a key in aux_data, it is replaced with the corresponding value converted to a string.

- Placeholder removal

  If an unreplaced placeholder remains and is enclosed in `[[[` and `]]]`, that portion will be removed.

- `{dialogue_history}` does not need to be specified in the templates.


### Process Details

- At the beginning of the dialog, the value of `first_system_utterance` in the block configuration is returned as system utterance.
- In the second and subsequent turns, the prompt template is given to LLM and the returned string is returned as the system utterance.

### Extraction of aux_data from System Utterances

Same as {numref}`extract_aux_data`.


