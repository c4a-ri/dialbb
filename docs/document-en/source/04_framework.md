(framework)=
# Framework Specifications

This chapter describes DialBB as a framework.

It assumes that the reader is familiar with Python programming.

## Input and Output

The main module of DialBB provides a class API. It accepts user utterances and auxiliary information in JSON-like dictionary form and returns system utterances and auxiliary information in the same form.

The main module operates by calling blocks in sequence. Each block receives dictionary data and returns dictionary data.

The block classes used by an application and their input and output mappings are defined in the application's configuration file.

### The DialogueProcessor Class

An application is created by instantiating `dialbb.main.DialogueProcessor`.

The basic usage is as follows.

- Assume that DialBB has been installed according to the GitHub README, or that `dialbb` is available on the module search path.

- In your application code, create a `DialogueProcessor` instance and call its `process` method.

  ```python
  from dialbb.main import DialogueProcessor

  dialogue_processor = DialogueProcessor(<configuration file>, <additional configuration>)
  response = dialogue_processor.process(<request>, initial=True)  # start of a dialogue session
  response = dialogue_processor.process(<request>)  # subsequent turns
  ```

`<additional configuration>` is a dictionary whose keys must be strings, for example:

```text
{
  "<key1>": <value1>,
  "<key2>": <value2>,
  ...
}
```

This is merged with the data loaded from the configuration file. If the same key appears in both places, the value from the additional configuration is used.

`<request>` and `response` are dictionary objects described below.

`DialogueProcessor.process` is **not** thread-safe.

### Request

#### At the Start of the Session

The request has the following form.

```text
{
  "user_id": <user ID string>,
  "aux_data": <auxiliary data object>
}
```

- `user_id` is required.
- `aux_data` is optional.
- `<user ID>` is a unique identifier for a user. It is used when the same user interacts with the application multiple times and the application needs to retain earlier context.
- `<auxiliary data>` is used to send client-side state to the application. It is a JSON object whose content depends on the application.

#### After the Session Starts

The request has the following form.

```text
{
  "user_id": <user ID string>,
  "session_id": <session ID string>,
  "user_utterance": <user utterance string>,
  "aux_data": <auxiliary data object>
}
```

- `user_id`, `session_id`, and `user_utterance` are required.
- `aux_data` is optional.
- `<session ID>` is the session identifier returned by the server.
- `<user utterance string>` is the utterance entered by the user.

### Response

The response has the following form.

```text
{
  "session_id": <session ID string>,
  "system_utterance": <system utterance string>,
  "user_id": <user ID string>,
  "final": <boolean flag indicating whether the dialogue has ended>,
  "aux_data": <auxiliary data object>
}
```

- `<session ID>` is the identifier of the dialogue session. A new session ID is generated when a new session starts. When an external database is used, a hash value is used.
- `<system utterance string>` is the system response.
- `<user ID>` is the user ID that was sent in the request.
- `<final>` indicates whether the dialogue has ended.
- `<auxiliary data>` is data sent from the application to the client, for example server-side state.

## WebAPI

Applications can also be accessed through the Web API.

### Server Startup

Assume that DialBB has been installed according to the GitHub README.

Start the server with the following command.

```sh
dialbb-server [--port <port>] <config file>
```

The default port number is `8080`.

### Connection from a Client at the Start of a Session

- URI

  ```text
  http://<server>:<port>/init
  ```

- Request header

  ```text
  Content-Type: application/json
  ```

- Request body

  The same JSON structure as the class API request.

- Response

  The same JSON structure as the class API response.

### Connection from a Client After the Session Starts

- URI

  ```text
  http://<server>:<port>/dialogue
  ```

- Request header

  ```text
  Content-Type: application/json
  ```

- Request body

  The same JSON structure as the class API request.

- Response

  The same JSON structure as the class API response.

(configuration)=
## Configuration

The configuration is dictionary data, typically provided as a YAML file.

The only required top-level element is `blocks`. This is a list of block configurations.

```yaml
blocks:
  - <block configuration>
  - <block configuration>
  ...
```

Each block configuration requires the following elements.

- `name`

  The name of the block. It is used in logs.

- `block_class`

  The class name of the block. It should be written as a path relative to a module search path entry in `sys.path`. Paths specified in `PYTHONPATH` are included in `sys.path`.

  The directory containing the configuration file is automatically added to the module search path.

  Built-in block classes should be specified in the form `dialbb.builtin_blocks.<module name>.<class name>`. A path relative to `dialbb.builtin_blocks` is also accepted, but deprecated.

- `input`

  This defines the mapping from the main module to the block. It is a dictionary whose keys are names used inside the block and whose values are keys in the blackboard maintained by the main module.

  ```yaml
  input:
    sentence: canonicalized_user_utterance
  ```

  In this example, `input['sentence']` inside the block refers to `blackboard['canonicalized_user_utterance']` in the main module.

  If the specified blackboard key does not exist, the corresponding input element becomes `None`.

- `output`

  This defines the mapping from the block back to the main module. Like `input`, it is a dictionary whose keys are names used inside the block and whose values are keys in the blackboard.

  ```yaml
  output:
    output_text: system_utterance
  ```

  If the block returns a dictionary named `output`, the following assignment is performed.

  ```python
  blackboard['system_utterance'] = output['output_text']
  ```

  If `blackboard` already has `system_utterance`, the value is overwritten.

## Retaining Dialogue History

### Retaining Dialogue History in the Blackboard

The `dialogue_history` element of `blackboard` stores dialogue history in the following format.

```text
[
  {
    "speaker": "user",
    "user_id": <input user_id, or "" if none is included>,
    "aux_data": <input aux_data, or {} if none is included>,
    "utterance": ""
  },
  {
    "speaker": "system",
    "aux_data": <output aux_data, or {} if none is included>,
    "utterance": <system utterance string>
  },
  {
    "speaker": "user",
    "user_id": <input user_id, or "" if none is included>,
    "aux_data": <input aux_data, or {} if none is included>,
    "utterance": <user utterance string>
  },
  ...
]
```

(context_db)=
### Storing Dialogue History in an External Database

When a DialBB application is run as a web server behind a load balancer, a single session may be handled by different instances. In that case, context can be stored in an external database such as MongoDB.

To use an external database, specify `context_db` in the block configuration as follows.

```yaml
context_db:
  host: localhost
  port: 27017
  user: admin
  password: password
```

Each key has the following meaning.

- `host` (`str`)

  The hostname where MongoDB is running.

- `port` (`int`, default `27017`)

  The port number for MongoDB.

- `user` (`str`)

  The username used to access MongoDB.

- `password` (`str`)

  The password used to access MongoDB.

## How to Make Your Own Blocks

Developers can create their own blocks.

A block class must inherit from `dialbb.abstract_block.AbstractBlock`.

### Methods to Implement

- `__init__(self, *args)`

  The constructor should be defined as follows.

  ```python
  def __init__(self, *args):
      super().__init__(*args)
      <block-specific processing>
  ```

- `process(self, input: Dict[str, Any], session_id: str = False) -> Dict[str, Any]`

  This method processes `input` and returns output. The relationship between the block's input and output and the main module's blackboard is defined in the configuration. See {numref}`configuration`.

  `session_id` is a string passed from the main module and is unique to each dialogue session.

### Available Variables

- `self.config` (dictionary)

  The full application configuration as dictionary data.

- `self.block_config` (dictionary)

  The block configuration for the current block.

- `self.name` (string)

  The name of the block written in the configuration.

- `self.config_dir` (string)

  The directory containing the configuration file. It is also called the application directory.

### Available Methods

#### Logging

The following logging methods are available.

- `log_debug(self, message: str, session_id: str = "unknown")`

  Outputs a debug-level log to standard error.

- `log_info(self, message: str, session_id: str = "unknown")`

  Outputs an info-level log to standard error.

- `log_warning(self, message: str, session_id: str = "unknown")`

  Outputs a warning-level log to standard error.

- `log_error(self, message: str, session_id: str = "unknown")`

  Outputs an error-level log to standard error. In debug mode, it raises an exception.

## Debug Mode

If the environment variable `DIALBB_DEBUG` is set to `yes` when Python starts, ignoring case, the program runs in debug mode. In that case, `dialbb.main.DEBUG` is `True`. Blocks created by application developers can also refer to this value.

If `dialbb.main.DEBUG` is `True`, the logging level is set to `debug`; otherwise it is set to `info`.

## Loading Environment Variables

In addition to `DIALBB_DEBUG`, environment variables are used for settings such as API keys for commercial LLMs. These variables may be set in the shell, but they can also be written in a `.env` file in the current working directory when the application starts.

```text
DIALBB_DEBUG=yes
OPENAI_API_KEY=....
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
```

Environment variables that are already set are **not overwritten** by entries in `.env`.

## Test

(test_scenario)=
### Test Using Test Scenarios

You can test an application with test scenarios using the following command.

```sh
dialbb-test <application configuration file> <test scenario> [--output <output file>]
```

A test scenario is a text file in the following format.

```text
----init...
System: <system utterance>
User: <user utterance>
System: <system utterance>
User: <user utterance>
...
----init...
System: <system utterance>
User: <user utterance>
...
```

Each session separator is a string beginning with `----init`.

The test script sends each user utterance to the application in order and receives the system utterance. If the returned system utterance differs from the one in the script, a warning is issued.

When the test finishes, the dialogue can be written out in the same format as the test scenario, including the actual system utterances. Comparing the expected scenario with the output file makes it easy to inspect response changes.

(test_requests)=
### Test Using Test Requests

Test scenarios cannot include `aux_data`. To test inputs that contain `aux_data`, use test requests instead.

Run the test with the following command.

```sh
dialbb-send-test-requests <application configuration file> <test request file>
```

A test request file is a JSON file in the following format.

```text
[
  [
    <first input of the first session>,
    <second input of the first session>,
    ...
  ],
  [
    <first input of the second session>,
    <second input of the second session>,
    ...
  ],
  ...
]
```

Each input has one of the following forms.

- First input of a session without `aux_data`

  ```text
  {"user_id": <user ID>}
  ```

- First input of a session with `aux_data`

  ```text
  {
    "user_id": <user ID>,
    "aux_data": <aux_data dictionary>
  }
  ```

- Second and subsequent inputs without `aux_data`

  ```text
  {
    "user_id": <user ID>,
    "user_utterance": "<user utterance text>"
  }
  ```

- Second and subsequent inputs with `aux_data`

  ```text
  {
    "user_id": <user ID>,
    "user_utterance": "<user utterance text>",
    "aux_data": <aux_data dictionary>
  }
  ```

The first input of each session is sent as-is. For the second and later inputs, `session_id` is added automatically before the request is sent to the DialBB application.

`user_id` may be omitted. In that case, the tool inserts a default user ID.

The sample application [sample_apps/dst_stn_en/test_requests.json](c:/Users/nakano/system/dialbb/dialbb-next/sample_apps/dst_stn_en/test_requests.json) contains concrete examples, including `aux_data` values used for speech-input-related testing.

(sim_tester)=
### Test Using a User Simulator

DialBB includes a tester that uses an LLM-based user simulator.

#### Running the Sample

The following example uses the English LLM dialogue sample application.

- Install DialBB and extract the sample applications.

- Set your OpenAI API key in the environment variable `OPENAI_API_KEY`.

  ```sh
  export OPENAI_API_KEY=<your OpenAI API key>
  ```

- In the `sample_apps` directory, run the following command.

  ```sh
  dialbb-sim-tester --app_config llm_dialogue_en/config.yml --test_config llm_dialogue_en/simulation/config.yml --output _output.txt
  ```

- The result is written to `_output.txt`.

- To launch the tester from a Python program, use the following code.

  ```python
  from dialbb.sim_tester.main import test_by_simulation

  for _ in test_by_simulation(
      "llm_dialogue_en/simulation/config.yml",
      "llm_dialogue_en/config.yml",
      output_file="_output.txt",
  ):
      pass
  ```

#### Specifications

- Startup options

  ```sh
  dialbb-sim-tester --app_config <DialBB application configuration file> --test_config <test configuration file> --output <output file>
  ```

- Test configuration file

  A YAML file containing the following keys.

  - `model` (string, required)

    Model specifier. Use the form `provider:model_name`, for example `google_genai:gemini-2.0-flash-001`. OpenAI GPT models such as `gpt-4o` and `gpt-4o-mini` may omit the `openai:` prefix.

  - `settings` (list of objects, required)

    A list of settings. Each setting may contain the following elements.

    - `prompt_template` (string, required)

      Path to a text file containing a prompt template. The path is relative to the test configuration file.

    - `initial_aux_data` (string, optional)

      Path to a JSON file describing the `aux_data` sent in the initial request to the DialBB application. The path is relative to the test configuration file.

  - `temperatures` (list of floats, optional)

    A list of temperature values for the LLM. The default is `[0.7]`. A session is run for each combination of `settings` and `temperatures`.

  - `max_turns` (integer, optional)

    The maximum number of turns per session. The default is `15`.

- Function specification

  - `dialbb.sim_tester.main.test_by_simulation(test_config_file: str, app_config_file: str, output_file: str = None, json_output: bool = False, prompt_params: Dict[str, str] = None)`

    Parameters:

    - `test_config_file`: Path to the test configuration file.
    - `app_config_file`: Path to the DialBB application configuration file.
    - `output_file`: File path for dialogue log output.
    - `json_output`: Whether the output file should be JSON. If `False`, a text file is produced.
    - `prompt_params`: Dictionary of values to embed in the prompt. If the prompt template contains `{<key>}`, it is replaced with `<value>`.
