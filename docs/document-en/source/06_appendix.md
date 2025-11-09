# Appendix

## Frontend

DialBB comes with two sample frontends for accessing the Web API.

### Simple Frontend

You can access it at:

```
http://<host>:<port>
```

This frontend displays system and user utterances in speech bubbles.

It does not allow sending `aux_data`.

Information other than the system utterance included in the response is not displayed.

### Debug Frontend

You can access it at:

```
http://<host>:<port>/test
```

This frontend displays system and user utterances in a list format.

It allows sending `aux_data`.

The `aux_data` included in the response is also displayed.

## How to Use DialBB without Installing via pip

First, clone the GitHub repository. The cloned directory will be referred to as `<DialBB Directory>`.

```sh
git clone git@github.com:c4a-ri/dialbb.git <DialBB Directory>
```

Set the environment variable `PYTHONPATH`:

```sh
export PYTHONPATH=<DialBB Directory>:$PYTHONPATH
```

### Using the Class API

If you want to use DialBB via the class API, start Python and import the necessary modules or classes from `dialbb`:

```python
from dialbb.main import DialogueProcessor
```

### Using the Web API

To use DialBB as a Web API, specify the configuration file and start the server:

```sh
$ python <DialBB Directory>/run_server.py [--port <port>] <config file>
```

The default `port` (port number) is 8080.


## Tester Using a User Simulator

A tester using a user simulator that uses an LLM (ChatGPT) is included.

### How to Run the Sample

The following explains how to run it using Bash. If you are using Windows Command Prompt, please adjust accordingly.

- Install DialBB and download and extract the sample application.

- Set the OpenAI API key to the environment variable  `OPENAI_API_KEY`.

  ```sh
  export OPENAI_KEY=<Your OpenAI API Key>
  ```

- In the directory where the sample application is extracted (`sample_apps`), run the following command:

  ```sh
  dialbb-sim-tester --app_config lab_app_en/config.yml --test_config lab_app_en/simulation/config.yml --output _output.txt
  ```

- The result will be written to `_output.txt`.

- To launch the tester from within a program, use the following code:

  ```python
  from dialbb.sim_tester.main import test_by_simulation
  
  test_by_simulation("lab_app_en/config.yml", 
                     "lab_app_en/simulation/config.yml", output="_output.txt")
  ```

### Specifications

- Startup options

  ```sh
  dialbb-sim-tester --app_config <DialBB application config file> --test_config <test config file> --output <output file>
  ```

- Test configuration file

  A YAML file containing the following keys:

  - `model`: (string, required) Name of the OpenAI GPT model, such as `gpt-4o` and `gpt-4o-mini`. `gpt-5` cannot be used.

  - `user_name`: (string, optional) The name representing the user in the dialogue history. Default is `"User"`.

  - `system_name`: (string, optional) The name representing the system in the dialogue history. Default is `"System"`.

  - `settings`: (list of objects, required) A list of settings. Each can contain the following:

    - `prompt_templates`: (list of strings, required) Paths to text files containing prompt templates. The paths are relative to the configuration file. 


    - `initial_aux_data`: (string, optional) Path to a JSON file containing content to be included in `aux_data` at the beginning of the dialogue when accessing the DialBB application. Path is relative to the configuration file.

  - `temperatures`: (list of floats, optional) A list of temperature parameters for GPT. Default is a single-element list `[0.7]`. Sessions will be conducted for all combinations of the length of `prompt_templates` × this list.

  - `max_turns`: (integer, optional) Maximum number of turns per session. Default is `15`.

- Function Specification

  - `dialbb.sim_test.main.test_by_simulation(test_config_file: str, app_config_file: str, output_file: str=None, json_output: bool=False, prompt_params: Dict[str, str])`

    Parameters:

    - `test_config_file`: Path to the test configuration file.

    - `app_config_file`: Path to the DialBB application configuration file.

    - `output_file`: File to write the dialogue logs to.

    - `json_output`: Whether the output file should be in JSON format. If `False`, it will be a text file.

    - `prompt_params`: Dictionary of parameters to embed into the prompt. If the prompt template contains `{<key>}`, it will be replaced with `<value>`.


## Discontinued Features

### Snips Understander Built-in Block

As Snips has become challenging to install with Python 3.9 and above, it was discontinued in version 0.9. Please use the LR-CRF Understander built-in block as an alternative.

### Whitespace Tokenizer and Sudachi Tokenizer Built-in Blocks

These blocks were discontinued in version 0.9. If you use LR-CRF Understander or ChatGPT Understander, there is no need for the Tokenizer blocks.

### Snips+STN Sample Application

This sample application was discontinued in version 0.9.

