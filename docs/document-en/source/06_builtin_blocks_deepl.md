
(builtin-blocks)=
# Specification of built-in block class

Built-in block classes are block classes that are included in DialBB in advance.

The normalization block class has been changed in ver 0.3. In addition, a new block class for word s
egmentation has been introduced.

The SNIPS language understanding input has changed accordingly.

## Japanese canonicalizer (Japanese string canonicalization block)
(`dialbb.builtin_blocks.preprocess.japanese_canonicalizer.JapaneseCanonicalizer`)

Normalizes the input string.

### Input/Output

- input
  - `input_text`: Input string (string)
    - Example: "I like CUP Noodle."

- output (e.g. of dynamo)
  - `output_text`: string after normalization (string)
    - Example: "I like cupnoodle."

### Description of process

Performs the following processing on the input string.

- Delete spaces before and after
- upper-case alphabetic characters → lower-case alphabetic characters
- Line Break Deletion
- Full-width to half-width conversion (excluding katakana)
- Deleting Spaces
- Unicode Normalization (NFKC)

## Simple canonicalizer (simple string canonicalizer block)

(`dialbb.builtin_blocks.preprocess.simple_canonicalizer.SimpleCanonicalizer`)

Normalizes user input sentences. The main target language is English.

### Input/Output

- input
  - `input_text`: Input string (string)
    - Example: "I like ramen".

- output (e.g. of dynamo)
  - `output_text`: string after normalization (string)
    - Example: "i like ramen".

### Description of process

Performs the following processing on the input string.

- Delete spaces before and after
- upper-case alphabetic characters → lower-case alphabetic characters
- Line Break Deletion
- Convert a sequence of spaces into a single space


## Sudachi tokenizer (Sudachi-based Japanese word segmentation block)

(`dialbb.builtin_blocks.tokenization.sudachi_tokenizer.SudachiTokenizer`)

Split the input string into words using [Sudachi](https://github.com/WorksApplications/Sudachi).

### Input/Output

- input
  - `input_text`: Input string (string)
    - E.g., "I want ramen."

- output (e.g. of dynamo)
  - `tokens`: list of tokens (list of strings)
    - Examples: ['I', 'is', 'ramen', 'is', 'eat', 'want'].
  - `tokens_with_indices`: List of tokens (list of objects of class `dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`). TokenWIthIndices`: A list of token information (a list of objects of class `dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`).

### Description of process

Word splitting using Sudachi's `SplitMode.C`.

If the value of `sudachi_normalization` in the block configuration is `True`, Sudachi normalization is performed.
The default value is `False`.

## Whitespace tokenizer (whitespace-based word segmentation block)

(`dialbb.builtin_blocks.tokenization.whitespace_tokenizer.WhitespaceTokenizer`)

Splits input into words separated by spaces. This is mainly for English.

### Input/Output

- input
  - `input_text`: Input string (string)
    - Example: "i like ramen".

- output (e.g. of dynamo)
  - `tokens`: list of tokens (list of strings)
    - Example: ['i','like','ramen'].
  - `tokens_with_indices`: List of token information (list of objects of class `dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`). TokenWIthIndices`: A list of token information (a list of objects of class `dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`) that contains not only the token but also the starting position of the token from the first character of the original string to the last character.

### Description of process

The simple normalization block splits normalized input into words separated by whitespace.


## SNIPS understander (language understanding block using SNIPS)

(`dialbb.builtin_blocks.understanding_with_snips.snips_understander.Understander`)  

Determines user utterance types (also called intents) and extracts slots using [SNIPS_NLU](https://snips-nlu.readthedocs.io/en/latest/).

If the `language` element of the configuration is `ja`, the language understanding is Japanese, and if it is `en`, the language understanding is English.
For Japanese, morphological analysis is performed using before applying SNIPS.

At startup, this block reads the knowledge for language understanding written in Excel, changes it to SNIPS training data, and builds the SNIPS model.
At runtime, the SNIPS model is used to understand the language.

### Input/Output

- input
  - `tokens`: list of tokens (list of strings)
    - Examples: ['like','na','of','is','soy sauce'].
  
- output (e.g. of dynamo)
  - `nlu_result`: language understanding result (dictionary type or list of dictionary types)
    
	  - If the parameter `num_candidates` of the 	block configuration described below is 1, the language understanding result is a dictionary type in the following format.
	
    ```json
	     {"type": <user speech type (intent)>,. 
	      "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}
	    ````
	  
	    The following is an example.
	  
    ```json
	     {"type": "I like a particular ramen", "slots": {"favorite_ramen": "soy sauce ramen"}}
	    ````
	  
  - If `num_candidates` is greater than or equal to 2, it is a list of multiple candidate comprehension results.
	  
    ```json
	     [{"type": <user speech type (intent)>, 
	       "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}, ...
	      {"type": <user speech type (intent)>,. 
	       "slots": {<slot name>: <slot value>, ... , <slot name>: <slot value>}}, ...
	      ....]
	    ````

### Block configuration parameters

- `knowledge_file` (string)

  Specify the Excel file that describes the knowledge. The file must be relative to the directory where the configuration file is located.

- `function_definitions` (string)

  The name of the module that defines the   dictionary function (see {ref}`dictionary_function`). If there are multiple modules, connect them with `':'`. The module must be in the module search path. (The directory containing the configuration files is in the module search path.)

- `flags_to_use` (list of strings)

  If one of these values is written in the `flag` column of each sheet, it is read. If this parameter is not set, all rows are read.

- `canonicalizer`. 

   Specify the normalization information to be performed when converting language comprehension knowledge to SNIPS training data.

   - `class`.
   
      Specifies the class of the normalization block. Basically, specify the same normalization block used in the application.
	  
- `tokenizer`. 

   Specify the word segmentation information to be used when converting language comprehension knowledge to SNIPS training data.

   - `class`.
   
      Specifies the class of the word segmentation block. Basically, specify the same word segmentation block used in the application.
	  
   - `sudachi_normalization` (Boolean; must be `False` by default). Default value `False`)

      If Sudachi Tokenizer is used       for word segmentation, Sudachi normalization is performed when this value is `True`.

- `num_candidates` (Integer. Default value `1`)

   Specifies the maximum number of language understanding results (n for n-best).

- `knowledge_google_sheet` (hash)

  - This section describes information for using Google Sheet instead of Excel. (For the settings for using Google Sheet, refer to [Kohata-san's article](https://note.com/kohaku935/n/nc13bcd11632d), but the UI of the Google Cloud Platform settings screen is slightly different from this article. )
  

    - `sheet_id` (string)

      Google Sheet ID.

    - `key_file` (string)

      Specify the key file to access the Goole Sheet API as a relative path from the configuration file directory.


(nlu_knowledge)=

### Language Comprehension Knowledge

Linguistic Comprehension Knowledge consists of the following four sheets.

| sheet name | contents |
| ---------- | -------------------------------------- |
| utterances | examples of utterances by type |
| slots | relationship between slots and entities |
| entities | Information about entities |
| dictionary | dictionary entries and synonyms per entity |

The sheet name can be changed in the block configuration, but since it is unlikely to be changed, a detailed explanation is omitted.

(Note) The column name of each sheet has been changed in ver0.2.0.

#### utterances sheet

Each row consists of the following columns

- `flag`.      

   Flags to be used or not, such as Y: yes, T: test, etc. are often written. Which flag rows to use is described in the configuration. In the configuration of the sample application, all lines are set to be used.

- `type`.     

   Type of speech (Intent)        

- `utterance`. 

   Example of speech. A slot is represented by `(<language expression corresponding to the slot>)[<slot name>]`, as in `(I like (pork bone ramen)[favorite_ramen]. Note that the language expression corresponding to a slot does not = the slot value that appears in the language comprehension result (i.e., is sent to manager). If the language expression is from the `synonyms` column of the `dictionary` sheet, the slot value will be from the `entity` column of the `dictionary` sheet.

It is acceptable to have other columns in the sheets used in this block as well as in the utterances sheet.

#### slotsheet

Each row consists of the following columns

- `flag`.

  Same as on the TUTTERANCE sheet

- `slot name`. 

  Slot name, used in the speech examples in the utterances sheet. Also used in the language comprehension results.

- `entity class`.

  Entity class name. This indicates what type of noun phrase the slot value is. Different slots may have the same entity class. For example, `I want to buy an express ticket from (Tokyo)[source_station] to (Kyoto)[destination_station]`, both `source_station, destination_station` have entity of class `station`. Both `source_station and `destination_station` are entities of the `station` class.
  You can use a dictionary function (of the form `dialbb/<function name>`) as the value of the   `entity class` column. This allows you to obtain a dictionary description with a function call instead of writing the dictionary information on a dictionary sheet (e.g. `dialbb/location`). （The function (e.g. `dialbb/location`) is described in "{ref}`dictionary_function`" below.
  The value of the entity class column can also be a SNIPS [builtin entity](https://snips-nlu.readthedocs.io/en/latest/builtin_entities.html). (e.g. `snips/city`)

  If you use the   SNIPS builtin entity, you must install it as follows

```sh
	$ snips-nlu download-entity snips/city en
````

Accuracy and other aspects of the 	SNIPS builtin entity have not been fully verified.

#### entities sheet

Each row consists of the following columns

- `flag`.

   Same as on the TUTTERANCE sheet

- `entity class`.

  Entity class name If a dictionary function is specified on the slots sheet, the same dictionary function name must be written here.

- `use synonyms`.

  [Synonyms or not](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#entity-values-synonyms) (`Yes` or `No`)

- `automatically extensible`.

  [Whether values not in dictionary are recognized or not](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#auto-extensible) (`Yes` or `No`)

- `matching strictness`.

  [Strictness of matching entities](https://snips-nlu.readthedocs.io/en/latest/api.html) `0.0` - `1.0`.

#### dictionary sheet

Each row consists of the following columns

- `flag`.

  Same as on the TUTTERANCE sheet

- `entity class`.

   entity class name

- `entity`.

   The name of the dictionary entry. Also included in the language understanding result.

- `synonyms`.

   Synonyms joined by `,` or `, ` or `, `

(dictionary_function)=
#### Dictionary function definitions by developers

Dictionary functions are mainly used to retrieve dictionary information from external databases.

Dictionary functions are defined in the module specified by `dictionary_function` in the block configuration.

The dictionary function takes configuration and block configuration as arguments. It is assumed that the configuration and block configurations contain connection information to external databases.

The return value of the dictionary function is a list of dictionary types of the form `{"value": <string>, "synonyms": <list of strings>}`. The ``synonyms"`` key is optional.

Examples of dictionary functions are shown below.

````python
def location(config: Dict[str, Any], block_config: Dict[str, Any]) \
    -> List[Dict[str, Union[str, List[str]]]]:.
    return [{"value": "Sapporo", "synonyms": ["Sapporo", "Sapporo"]}, }
            {"value": "Ogikubo", "synonyms": ["ogikubo"]},.
            {"value": "Tokushima"}]
````

#### SNIPS training data

When the application is launched, the above knowledge is converted into SNIPS training data and a model is created.

The SNIPS training data is `_training_data.json` in the application directory. By looking at this file, you can check if the conversion is successful.

(stn_manager)=
## STN manager (state transition network-based dialogue management block)

(`dialbb.builtin_blocks.stn_manager.stn_management`)  

Dialogue management is performed using a State-Transition Network.

- input
  - `sentence`: User utterance after normalization (string)
  - `nlu_result`: language understanding result (dictionary type or list of dictionary types)
  - `user_id`: User ID (string)
  - `aux_data`: auxiliary data (dictionary type) (not required, but recommended)
- output (e.g. of dynamo)
  - `output_text`: System speech (string)
     Example:
	  ````
	  "So you like soy sauce ramen."
	  ````
  - `final`: boolean flag indicating whether the dialog is finished or not.
  - `aux_data`: auxiliary data (dictionary type) (changed in ver. 0.4.0)
     The auxiliary data of the input is updated in the action function described below, including the ID of the transitioned state. Updates are not necessarily performed in the action function. The transitioned state is added in the following format.
     ```json
	 {"state": "I like a particular ramen" }
     ````
     
### Block configuration parameters

- `knowledge_file` (string)

  Specifies an Excel file describing the scenario. The file must be relative to the configuration file directory.

- `function_definitions` (string)

  The name of the module that defines the   scenario function (see {ref}`dictionary_function`). If there are multiple modules, connect them with `':'`. The module must be in the module search path. (The directory containing the configuration files is in the module search path.)

- `flags_to_use` (list of strings)

  If one of these values is written in the `flag` column of each sheet, it is read.

- `knowledge_google_sheet` (hash)

  Same as SNIPS Understander.

- `scenario_graph`: (Boolean; default value is `False`). Default value `False`)

   If this value is `True`, the values in the `system utterance` and `user utterance example` columns of the scenario sheet are used to create the graph. This allows the scenario creator to intuitively see the state transition network.
   
- `repeat_when_no_available_transitions` (Boolean; added in ver. 0.4.0) Default value `False`; added in ver. 0.4.0)

   When this value is `True`, if there is no transition other than the default transition (see below) that matches the condition, the same utterance is repeated without transition.

(scenario)=
### Dialogue Management Knowledge Description

The dialog management knowledge (scenario) is a scenario sheet in an Excel file.

Each row of the sheet represents a transition. Each row consists of the following columns

- `flag`.

  Same as on the TURTARANCE sheet.

- `state`.

  Transition source state name

- `system utterance`.

  Candidate system utterances generated in the `state` state. The {<variable>} in the system utterance string is replaced by the value assigned to the variable during the dialogue. There can be multiple lines with the same `state`, but all `system utterance` candidates for the same `state` line are generated randomly.

- `user utterance example`.

  Example of user speech. It is only written to understand the flow of the dialogue, and is not used by the system.

- `user utterance type`.

  The type of user utterance resulting from linguistic understanding of the user utterance. The condition of the transition.

- `conditions`.

  Condition (sequence of conditions). A function call that represents a condition for a transition. There can be more than one. If there are multiple conditions, they are concatenated with `;`. Each condition has the form `<function name>(<argument 1>, <argument 2>, ..., <argument n>)`. <argument n>)`. The number of arguments can be zero. See {ref}`arguments` for the arguments that can be used in each condition.

- `actions`.

  Action (sequence of actions). The function call to execute when the transition occurs. There can be multiple calls. If there is more than one, they are concatenated with `;`. Each condition has the form `<function name>(<argument 1>, <argument 2>, ..., <argument n>)`. <argument n>)`. The number of arguments can be zero. See {ref}`arguments` for the arguments that can be used in each condition.

- `next state`.

  Transition destination state name

（You may have other columns on the sheet (for use as notes).

If the `user utterance type` of the transition represented by each line is empty or matches the result of language understanding, and if the `conditions` are empty or all of them are satisfied, the condition for the transition is satisfied and the transition is made to the `next state` state. In this case, the action described in `actions` is executed.

Rows with the same `state` column (transitions with the same source state) are checked to see if they satisfy the transition conditions, starting with the one written above.

The default transition (a line with neither `user utterance type` nor `conditions` columns empty) must have a `state` column written at the bottom of the same line.


### Special status

The following state names are predefined.

- `#prep`.

  Ready state. If this state exists, a transition from this state is attempted at the beginning of the dialog (when the client first accesses the server). The `state` column is checked to see if all the conditions in the `conditions` of the row with the value `#prep` are satisfied, and if so, the action in the `actions` of that row is executed, then the transition to the `next state` is made and the system speech in that state is output ...

  It is used to change the initial system utterance or state depending on the situation. The Japanese sample application changes the greeting depending on the time at which the dialog takes place.

  This state of readiness is not necessary.
  The destination from `#prep` does not have to be `#initial`. (ver. 0.4.0)

- `#initial`.
  Initial state. If there is no `#prep` state, it starts in this state when the dialog starts (when the client first accesses the system), and the system utterances in this state are put into `output_text` and returned to the main process.
  
There must be either `#prep` or `#initial` state.

- `#error`.

  Moves to this state when an internal error occurs. Generates a system utterance and exits.

A state ID beginning with `#final`, such as `#final_say_bye`, indicates the final state.
In the final state, the system generates a system utterance and terminates the dialog.


### Conditions and Actions

#### Contextual information

STN Manager maintains contextual information for each dialogue session. The context information is a set of variables and their value pairs (python dictionary type data), and the values can be any data structure.

Condition and action functions access contextual information.

The following key/value pairs are pre-set in the context information.

| key | value |
| ------------- | ------------------------------------------------------------ |
| _current_state_name | name of the state before transition (string)
| _config | dictionary type data created by reading config file |
| _block_config | Configuration part of the dialog management block in the config file (dictionary type data)
| _aux_data | aux_data (data of dictionary type) received from main process
| _previous_system_utterance | previous system utterance (string)
| _dialogue_history | Dialogue history (list)


The dialog history is in the following form

````python
[
  {"speaker": "user", "user".
   utterance": <user utterance after normalization (string)>},.
  {"speaker": "system", "system".
   utterance": <system utterance>},.
  {"speaker": "user", "user".
   utterance": <user utterance after normalization (string)>},.
  {"speaker": "system", "system".
   utterance": <system utterance>},.
  ...
]
````

In addition to these, new key/value pairs can be added within the action function.

(arguments)=

#### Function Arguments

The following types of function arguments are used in conditions and actions.

- Special variables (strings beginning with `#`)

  The following types are available

  - `#<slot name>`.
    Slot value of the     language understanding result of the previous user utterance (the input `nlu_result` value). If the slot value is empty, it is an empty string.
  - `#<key for auxiliary data>`.
    The value of this key in the     input aux_data. For example, in the case of `#emotion`, the value of `aux_data['emotion']`. If this key is missing, it is an empty string.
  - `#sentence`.
    Immediate previous user utterance (normalized)
  - `#user_id`.
    User ID (string)

- Variables (strings beginning with `*`)

  The value of a variable in context information in the form `*<variable name>`. The value of a variable must be a string. If the variable is not in the context information, it is an empty string.

- Variable reference (string beginning with &)

  The `&&<contextual variable name>` form is used to use contextual variable names in function definitions.

- Constant (string enclosed in `""`)

  It means the string as it is.


### function definition

Functions used in conditions and actions are either built-in to DialBB or defined by the developer. Functions used in conditions return bool values, while functions used in actions return nothing.

#### Built-in Functions

Built-in functions include

- Functions used in conditions

  - `_eq(x, y)`

    Returns `True` if `x` and `y` are the same.
    Example: `_eq(*a, "b"`): returns `True` if the value of variable `a` is `"b"`.
    `_eq(#food, "ramen")`: returns `True` if `#food` slot is `"ramen"`.

  - `_ne(x, y)`

    Returns `True` if `x` and `y` are not the same.

    Example: `_ne(*a, *b)`: returns `True` if the value of variable `a` is different from the value of variable `b`.
    `_ne(#food, "ramen"):` Return `False` if `#food` slot is `"ramen"`.

  - `_contains(x, y)`

    Returns `True` if `x` contains `y` as a string.
    Example: contains(#sentence, "yes") : returns True if the user utterance contains "yes".

  - `_not_contains(x, y)`

    Returns `True` if `x` does not contain `y` as a string.

    Example: `_not_contains(#sentence, "yes")` : returns `True` if the user utterance contains `"yes"`.

  - `_member_of(x, y)`

    Returns `True` if the list formed by splitting `y` by `':'` contains the string `x`.

    Example: `_member_of(#food, "ramen:fried rice:dumplings")`

  - `_not_member_of(x, y)`

    Returns `True` if the list formed by splitting `y` by `':'` does not contain the string `x`.

    Example: `_not_member_of(*favorite_food, "ramen:fried_han:dumpling")`


- Functions used in actions

  - `_set(x, y)`

    Set `y` to the variable `x`.

    Example: `_set(&a, b)`: sets the value of `b` to `a`.
    `_set(&a, "hello")`: sets `a` to `"hello"`.

  - `_set(x, y)`

    Set `y` to the variable `x`.

    Example: `_set(&a, b)`: sets the value of `b` to `a`.
    `_set(&a, "hello")`: sets `a` to `"hello"`.

#### Function definition by developer

When the developer defines functions, he/she edits scenario_functions.py in the application directory.

````python
def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None: None
    location:str = ramen_map.get(ramen, "Japan")
    context[variable] = location
````

In addition to the arguments used in the scenario, as described above, a variable of dictionary type must be added to receive contextual information.

All arguments used in the scenario must be strings.

In the case of a special variable or variables, the value of the variable is passed as an argument.

In the case of a variable reference, the variable name without the `&`' is passed, and in the case of a constant, the string in `""` is passed.


### Continuous Transition
If a transition is made to a state where the first system utterance is `$skip`, the next transition is made immediately without returning a system response. This is used in cases where the second transition is selected based on the result of the action of the first transition.

### Processing when there are multiple candidate language comprehension results

If the input `nlu_result` is a list of data and contains multiple candidate language understanding results, the processing is as follows

Starting from the top of the list, check whether the `type` value of a candidate language understanding result is equal to the `user utterance type` value of one of the possible transitions from the current state, and use the candidate language understanding result if there is an equal transition.

If none of the candidate language comprehension results meet the above conditions, the first language comprehension result in the list is used.

### Subdialogue

If the destination state name is of the form `#gosub:<state name1>:<state name2>`, it transitions to the state `<state name1>` and executes a subdialogue starting there. If the destination state is `:exit`, it moves to the state `<state name2>`.

For example, if the destination state name is of the form `#gosub:request_confirmation:confirmed`, a subdialogue starting with `request_confirmatin` is executed, and when the destination state becomes `:exit`, it returns to `confirmed`. When the destination becomes `:exit`, it returns to `confirmed`.

It is also possible to transition to a subdialogue within a subdialogue.


### Mechanisms for handling voice input

In ver. 0.4.0, the following changes were made to address problems that occur when treating speech recognition results as input.

#### Add block configuration parameters

- `input_confidence_threshold` (float; default value `1.0`)

   If the input is a speech recognition result and its confidence is less than this value, it is considered low confidence. The confidence of the input is the value of `confidence` in `aux_data`. If there is no `confidence` key in `aux_data`, the confidence is considered high. In the case of low confidence, the process depends on the value of the parameter described below.
   
- `confirmation_request` (object)

   This is specified in the following form.
   
   ```yaml
   confirmation_request:.
     function_to_generate_utterance: <function name (string)
     acknowledgement_utterance_type: <user utterance type name of acknowledgement (string)
     denial_utterance_type: <name of user utterance type for affirmation (string)
   ````
   
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
   
  The `confirmation_request` and `utterance_to_ask_repetition` cannot be specified at the same time.
      

- `ignore_out_of_context_barge_in` (Boolean; must be `False` by default). Default value `False`) 

  If this value is `True`, the input is a barge-in utterance (the value of `barge_in` in the `aux_data` of the request is `True`), the conditions for a transition other than the default transition are not met (i.e. the input is not expected in the scenario), or the confidence level of the input is low the transition is not made. In this case, the `barge_in_ignored` of the response `aux_data` is set to `True`.

- `reaction_to_silence` (object)

   It has an `action` element. The value of the `action` key is a string that can be either `repeat` or `transition`. If the value of the `action` element is `transition`, the `action` key is required. The value of the `action` key is a string.

   If the input `aux_data` has a `long_silence` key and its value is `True`, and if the conditions for a transition other than the default transition are not met, then it behaves as follows, depending on this parameter

    - If this parameter is not specified, normal state transitions are performed.

    - If the value of `action` is `"repeat"`, the previous system utterance is repeated without state transition.
	
    - If the value of `action` is `transition`, then the transition is made to the state specified by `destination`.

#### Add built-in conditional functions

The following built-in conditional functions have been added

- `_confidence_is_low()` 

   Returns True if the value of `confidence` in the    input `aux_data` is less than or equal to the value of `input_confidence_threshold` in the configuration.

   
- `_is_long_silence()`

    Returns `True` if the value of `long_silence` in the     input `aux_data` is `True`.

#### Ignore last incorrect input

If the value of `rewind` in the input `aux_data` is `True`, a transition is made from the state before the last response.
Any changes to the dialog context due to actions taken during the previous response will also be undone.

This function is used when a user's speech is accidentally split in the middle during speech recognition and only the first half of the speech is responded to.

Note that the interactive context is restored, but not if you have changed the value of a global variable in an action function or the contents of an external database.









