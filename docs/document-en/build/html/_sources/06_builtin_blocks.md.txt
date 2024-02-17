(builtin-blocks)=
# Built-in Block Classes

Built-in block classes are block classes that are included in DialBB in advance.

Below, the explanation of the blocks that deal with only Japanese is omitted.

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
- Replaces upper-case alphabetic characters by lower-case characters.
- Deletes line breaks.
- Converts a sequence of spaces into a single space.

(whitespace_tokenizer)=
## Whitespace Tokenizer (Whitespace-based Word Segmentation Block)

(`dialbb.builtin_blocks.tokenization.whitespace_tokenizer.WhitespaceTokenizer`)

Splits input into words separated by spaces. This is mainly for English.

### Input/Output

- input
  - `input_text`: Input string (string)
    - Example: "i like ramen".

- output (e.g. of dynamo)
  - `tokens`: list of tokens (list of strings)
    - Example: ['i','like','ramen'].
  - `tokens_with_indices`: List of token information (list of objects of class `dialbb.tokenization.abstract_tokenizer.TokenWIthIndices`). Each token information includes the indices of start and end points in the input string.

### Process Details

Splits the input string canonicalized by the simple canonicalizer by whitespace.

(snips_understander)=
## Snips Understander (Language Understanding Block using Snips)

(`dialbb.builtin_blocks.understanding_with_snips.snips_understander.Understander`)  

Determines the user utterance type (also called intent) and extracts the slots using [Snips_NLU](https://snips-nlu.readthedocs.io/en/latest/).

Performs language understanding in Japanese if the `language` element of the configuration is `ja`, and language understanding in English if it is `en`. 

At startup, this block reads the knowledge for language understanding written in Excel, converts it into Snips training data, and builds the Snips model.

At runtime, it uses the created Snips model for language understanding.


### Input/Output

- input
  - `tokens`: list of tokens (list of strings)
    - Examples: `['I' 'like', 'chicken', 'salad' 'sandwiches']`.
  
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

- `function_definitions` (string)


   Specifies the name of the module that defines the dictionary functions (see {ref}`dictionary_function`). If there are multiple modules, connect them with `':'`. The module must be in the module search path. (The directory of the configuration file is in the module search path.)

- `flags_to_use` (list of strings)

   Specifies the flags to be used. If one of these values is written in the `flag` column of each sheet, it is read. If this parameter is not set, all rows are read.

- `canonicalizer` 

   Specifies the canonicalization information to be performed when converting language comprehension knowledge to Snips training data.

   - `class`
   
      Specifies the class of the normalization block. Basically, the same normalization block used in the application is specified.


- `tokenizer` 

   Specifies the tokenization information to be used when converting language understanding knowledge to Snips training data.

   - `class`
   
      Specifies the class of the tokenization block. Basically, the same tokenization block used in the application is specified.

- `num_candidates` (integer. Default value is `1`)

   Specifies the maximum number of language understanding results (n for n-best).

- `knowledge_google_sheet` (hash)

  - This specfies information for using Google Sheet instead of Excel.
  
    - `sheet_id` (string)

      Google Sheet ID.

    - `key_file`(string)

       Specify the key file to access the Google Sheet API as a relative path from the configuration file directory.

(nlu_knowledge)=

### Language Understanding Knowledge

Language understanding knowledge consists of the following four sheets.

| sheet name | contents |
| ---------- | -------------------------------------- |
| utterances | examples of utterances by type |
| slots | relationship between slots and entities |
| entities | Information about entities |
| dictionary | dictionary entries and synonyms per entity |

The sheet name can be changed in the block configuration, but since it is unlikely to be changed, a detailed explanation is omitted.

#### utterances sheet

Each row consists of the following columns

- `flag`      

   Flags to be used or not. `Y` (yes), `T` (test), etc. are often written. Which flag's rows to use is specified in the configuration. In the configuration of the sample application, all rows are used.


- `type`     

   User utterance type (Intent)        

- `utterance` 

   Example utterance. Each slot is annotated as `(<linguistic expression corresponding to the slot>)[<slot name>]`, as in `I like (chiken salad sandwiches)[favorite_sandwich].` Note that the linguistic expression corresponding to a slot does not always equal to the slot value that appears in the language understanding result (i.e., is sent to manager). If the linguistic expression eauals to the `synonyms` column of the `dictionary` sheet, the slot value will be the value of the `entity` column of the `dictionary` sheet.

The sheets that this block uses, including the utterance sheets, can have other columns than these.

#### slots sheet

Each row consists of the following columns.

- `flag`

  Same as on the utterance sheet.

- `slot name` 

  Slot name. It is used in the example utterances in the utterances sheet. Also used in the language understanding results.

- `entity class`

  Entity class name. This indicates what type of noun phrase the slot value is. Different slots may have the same entity class. For example, `I want to buy an express ticket from (Tokyo)[source_station] to (Kyoto)[destination_station]`, both `source_station` and `destination_station` have entity of class `station`. 

  You can use a dictionary function (of the form `dialbb/<function name>`) as the value of the   `entity class` column. This allows you to obtain a dictionary description with a function call instead of writing the dictionary information on a dictionary sheet (e.g. `dialbb/location`). 
  
  The function (e.g. `dialbb/location`) is described in "{ref}`dictionary_function`" below.

  The value of the entity class column can also be a [Snips built-in entity](https://snips-nlu.readthedocs.io/en/latest/builtin_entities.html). (e.g. `snips/city`)

  When you use Snips built-in entities, you need to install it as follows

  ```sh
  $ snips-nlu download-entity snips/city en
  ```

  Accuracy and other aspects of the Snips built-in entities have not been fully verified.

#### entities sheet

Each row consists of the following columns.

- `flag`

   Same as on the utterance sheet.

- `entity class`

   Entity class name. If a dictionary function is specified in the slots sheet, the same dictionary function name must be written here.

- `use synonyms`

  [Whether to use synonyms or not](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#entity-values-synonyms). (`Yes` or `No`)

- `automatically extensible`

  [Whether to recongize values not in dictionary or not](https://snips-nlu.readthedocs.io/en/0.20.0/data_model.html#auto-extensible). (`Yes` or `No`)

- `matching strictness`

  [Strictness of matching entities](https://snips-nlu.readthedocs.io/en/latest/api.html). `0.0` - `1.0`


#### dictionary sheet

Each row consists of the following columns

- `flag`

  Same as that of the utterance sheet.

- `entity class`

   entity class name.

- `entity`

   The name of the dictionary entry. It is also included in language understanding results.

- `synonyms`

   Synonyms joined by `','`.


(dictionary_function)=
#### Dictionary function definitions by developers

Dictionary functions are mainly used to retrieve dictionary information from external databases.

Dictionary functions are defined in the module specified by `dictionary_function` in the block configuration.

The dictionary function takes configuration and block configuration as arguments. It is assumed that the these contain connection information to external databases.

The return value of a dictionary function is a list of dicts of the form `{"value": <string>, "synonyms": <list of strings>}`. The ``synonyms"`` key is optional.

Examples of dictionary functions are shown below.


```python
def location(config: Dict[str, Any], block_config: Dict[str, Any]) \
    -> List[Dict[str, Union[str, List[str]]]]:
    return [{"value": "US", "synonyms": ["USA", "America"]},
            {"value": "California", "synonyms": ["CA"]},
            {"value": "Texas"}]
```


#### Snips training data

When the application is launched, the above knowledge is converted into Snips training data and a model is created.

The Snips training data is `_training_data.json` in the application directory. By looking at this file, you can check if the conversion is successful.

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

   If this value is `True`, the values in the `system utterance` and `user utterance example` columns of the scenario sheet are used to create the graph. This allows the scenario writer to intuitively see the state transition network.

- `repeat_when_no_available_transitions` (Boolean. Default value is `False`)

   When this value is `True`, if there is no transition other than the default transition (see below) that matches the condition, the same utterance is repeated without transition.

(scenario)=
### Dialogue Management Knowledge Description

The dialog management knowledge (scenario) is written in the scenario sheet in the Excel file.

Each row of the sheet represents a transition. Each row consists of the following columns

- `flag`

  Same as on the utterances sheet.

- `state`

  The name of the source state of the transition.

- `system utterance`

    Candidates of the system utterance generated in the `state` state. The {<variable>} in the system utterance string is replaced by the value assigned to the variable during the dialogue. There can be multiple lines with the same `state`, but all `system utterance` in the lines having the same `state` become system utterance candidates, and will be chosen randomely.

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

#### Contextual Information

STN Manager maintains contextual information for each dialogue session. The contextual information is a set of variables and their values (python dictionary type data), and the values can be any data structure.


Condition and action functions access contextual information.


The context information is pre-set with the following key-value pairs.

| key | value |
| ------------- | ------------------------------------------------------------ |
| _current_state_name | name of the state before transition (string)
| _config | dictionary type data created by reading configuration file |
| _block_config | The part of the dialog management block in the configiguration file (dictionary)
| _aux_data | aux_data (dictionary) received from main process
| _previous_system_utterance | previous system utterance (string)
| _dialogue_history | Dialogue history (list)



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
#### Function Arguments

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

  The value of a variable in contextual information. It is in the form `*<variable name>`. The value of a variable must be a string. If the variable is not in the context information, it is an empty string.

- Variable reference (string beginning with `&`)

  Refers to a contextual variable in function definitions. It is in the form `&<contextual variable name>` 

- Constant (string enclosed in `""`)

  It means the string as it is.


### Function Definitions

Functions used in conditions and actions are either built-in to DialBB or defined by the developers.The function used in a condition returns a boolean value, while the function used in an action returns nothing.


#### Built-in Functions

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
    
- Functions used in actions

  - `_set(x, y)`

    Sets `y` to the variable `x`.

    e.g.,  `_set(&a, b)`: sets the value of `b` to `a`.

    `_set(&a, "hello")`: sets `"hello"` to `a`.


  - `_set(x, y)`

    Sets `y` to the variable `x`.

    e.g., `_set(&a, b)`: sets the value of `b` to `a`. 

    `_set(&a, "hello")`: sets `"hello"` to `a`.

#### Function Definitions by the Developers


When the developer defines functions, he/she edits a file specified in `function_definition` element in the block configuration.

```python
def get_ramen_location(ramen: str, variable: str, context: Dict[str, Any]) -> None: 
    location:str = ramen_map.get(ramen, "Japan")
    context[variable] = location
```

In addition to the arguments used in the scenario, variable of dictionary type must be added to receive contextual information.

All arguments used in the scenario must be strings.
In the case of a special variable or variables, the value of the variable is passed as an argument.
In the case of a variable reference, the variable name without the `&`' is passed, and in the case of a constant, the string in `""` is passed.

### Reaction

In an action function, setting a string to `_reaction` in the context information will prepend that string to the system's response after the state transition.

For example, if the action function `_set(&_reaction, "I agree.")` is executed and the system's response in the subsequent state is "How was the food?", then the system will return the response "I agree. How was the food?".

### Continuous Transition

If a transition is made to a state where the first system utterance is `$skip`, the next transition is made immediately without returning a system response. This is used in cases where the second transition is selected based on the result of the action of the first transition.

### Dealing with Multiple Language Understanding Results

If the input `nlu_result` is a list that contains multiple language understanding results, the process is as follows.

Starting from the top of the list, check whether the `type` value of a candidate language understanding result is equal to the `user utterance type` value of one of the possible transitions from the current state, and use the candidate language understanding result if there is an equal transition. If none of the candidate language comprehension results meet the above conditions, the first language comprehension result in the list is used.

### Subdialogue

If the destination state name is of the form `#gosub:<state name1>:<state name2>`, it transitions to the state `<state name1>` and executes a subdialogue starting there. If the destination state is `:exit`, it moves to the state `<state name2>`.
For example, if the destination state name is of the form `#gosub:request_confirmation:confirmed`, a subdialogue starting with `request_confirmatin` is executed, and when the destination state becomes `:exit`, it returns to `confirmed`. When the destination becomes `:exit`, it returns to `confirmed`.
It is also possible to transition to a subdialogue within a subdialogue.

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

Note that the contextual information is reverted, but not if you have changed the value of a global variable in an action function or the contents of an external database.

(chatgpt_dialogue)=
## ChatGPT Dialogue (ChatGPT-based Dialogue Block)

(`dialbb.builtin_blocks.chatgpt.chatgpt_en.ChatGPT_Ja` (for Japanese), and `dialbb.builtin_blocks.chatgpt.chatgpt_en.ChatGPT_En` (for English))

Engages in dialogue using OpenAI's ChatGPT.

These classes are subclasses of `dialbb.built-in_blocks.chatgpt.chatgpt.ChatGPT`. By creating a new subclass of `dialbb.built-in_blocks.chatgpt.chatgpt.ChatGPT`, you can create a new block using ChatGPT.


### Input/Output

- Input

  - `user_utterance`: Input string (string)
  - `aux_data`: Auxiliary data (dictionary).
  - `user_id`: auxiliary data (dictionary)

- Output

  - `system_utterance`: Input string (string)
  - `aux_data`: auxiliary data (dictionary type)
  - `final`: boolean flag indicating whether the dialog is finished or not.

In `ChatGPT_Ja` and `ChatGPT_En`, the input `aux_data` and `user_id` are not used.
The output `aux_data` is the same as the input `aux_data` and `final` is always `False`, but
you can change this when you create a new subclass of `ChatGPT`.

When using these blocks, you need to set the OpenAI license key in the environment variable `OPENAI_KEY`.

### Block Configuration Parameters

- `first_system_utterance` (string, default value is `""`)

   This is the first system utterance of the dialog.


- `prompt_prefix` (string, default value is `""`)

   This is used for the ChatGPT prompt. 

- `prompt_postfix` (string, default value is `""`)

   This is used for the ChatGPT prompt. 

- `gpt_model` (string, default value is `gpt-3.5-turbo`)

   Open AI GPT model. You can specify `gpt-4` and so on.

### Process Details

- At the beginning of the dialog, the value of `first_system_utterance` in the block configuration is returned as system utterance.

- In the second and subsequent turns, the following prompt is given to ChatGPT and the returns are returned as the system utterance.

   As an example, the following prompt is given.
  
  ```
  The system can talk to the user intimately. 
  System: "Hello. Let's have a nice talk. What would you like to talk about?"
  User: "I would like to talk about movies."
  System: "Great. I love to talk about movies. Please tell me what movies you have seen recently and what your favorite genre is."
  User: "I saw the latest film by Hayao Miyazaki".
  Generate a subsequet system utterance with a maximum of 30 words.
  ```
  
  The ChatGPT response will look something like this

  ```
  System: "That's wonderful. Hayao Miyazaki's films are always wonderful. What did you think of the film?"
  ```
  
   The following strings are extracted from this and returned as system speech.

  ```
  That's wonderful. Hayao Miyazaki's films are always wonderful. What did you think of the film?
  ```

### Extending the ChatGPT Dialogue Block Class

As mentioned earlier, you can create a subclass of `dialbb.built-in_blocks.chatgpt.chatgpt.ChatGPT` and use it as your own block for flexible control changes.

When creating a subclass, implement the following methods

```python
_generate_system_utterance(self, dialogue_history: List[Dict[str, str]],.
                                 session_id: str, user_id: str, aux_data: Dict[str, Any
                                 aux_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any], bool]:.
```

- arguments

  - `dialogue_history` (list of dictionaries)

    The history of the dialog, represented as an array like this
  
   ```json
   [
     {
       "speaker": "system", 
       "utterance": <system utterance string>
      },
      {
        "speaker": "user", 
        "utterance": <user utterance string>
      },
      ...
   ]
   ```

  - `session_id` (string)

     session ID

  - `user_id` (string)

     user ID

  - `aux_data` (dictionary type)

     Auxiliary data received from the main process

- The return value is the following Tuple

  - `system_utterance` (string)

    system utterance

  - `aux_data` (dictionary)

     Updated auxiliary data
  
  - `final` (boolean)

     End of dialogue or not

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

`<label>` is a class of named entities. `<named entity>` is a found named entity, a substring of ``input_text`. If multiple named entities of the same class are found, they are concatenated with `':'`.

Example:
	 
```json
{ 
  "NE_Person": "John:Mary", 
  "NE_Dish": "Chiken Marsala"
}
```

See the spaCy/GiNZA model website for more information on the class of named entities.
	 
- `en-ginza-electra` (5.1.2):, https://pypi.org/project/ja-ginza-electra/

- `en_core_web_trf` (3.5.0):, https://huggingface.co/spacy/en_core_web_trfhttps://pypi.org/project/ja-ginza-electra/


### Block Configuration Parameters

- `model` (String: Required)

   The name of the spaCy/GiNZA model. It can be `ja_ginza_electra` (Japanese), `en_core_web_trf` (English), etc.

- `patterns` (object; Optional)

   Describes a rule-based named entity extraction pattern. The pattern is a YAML format of the one described in [spaCy Pattern Description](https://spacy.io/usage/rule-based-matching).

   
   The following is an example in Japanese.
   
   ```yaml
   patterns: Date
     - label: Date
       pattern: yesterday
     - label: Date
       pattern: The day before yesterday
   ```

### Process Details

Extracts the named entities in `input_text` using spaCy/GiNZA and returns the result in `aux_data`.

