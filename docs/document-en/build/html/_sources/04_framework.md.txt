(framework)=
# Framework Specifications

This section describes the specifications of DialBB as a framework. 

We assume that the reader has knowledge of Python programming.

## Input and Output

The main module of DialBB has the class API (method call), which accepts user utterance and auxiliary information in JSON format and returns system utterance and auxiliary information in JSON format.

The main module works by calling blocks in sequence. Each block receives data  formatted in JSON (Python dictionary type) and returns the data in JSON format.

The class and input/output specifications of each block are specified in the configuration file for each application.

### The DialogueProcessor Class

The application is built by creating an object of class `dialbb.main.DialogueProcessor`

This is done by the following procedure.


- Add the DialBB directory to the `PYTHONPATH` environment variable.

  ```sh
  export PYTHONPATH=<DialBB directory>:$PYTHONPATH
  ```

- In the application that uses DialBB, use the following DialogueProcessor
  and calls process method.

  ```python
  from dialbb.main import DialogueProcessor
  dialogue_processor = DialogueProcessor(<configuration file> <additional configuration>)
  response = dialogue_processor.process(<request>, initial=True)  # at the start of a dialogue session
  response = dialogue_processor.process(<request>) # when session continues
  ```
  
  `<additional configuration>` is data in dictionary form, where keys must be a string, such as
  
  ```json
  {
	"<key1>": <value1>,
    "<key2>": <value2>,
    ...
  }
  ```
  
  This is used in addition to the data read from the configuration file. If the same key is used in the
  configuration file and in the additional configuration, the value of the additional configuration is used.
  
   `<request>` and `response` are dictionary type data, described below.

   Note that `DialogueProcessor.process` is **not** thread safe.

### Request

#### At the start of the session

JSON in the following form.

  ```json
  {
    "user_id": <user id: string>,
    "aux_data": <auxiliary data: object (types of values are arbitrary)>}
  }
  ```

  - `user_id` is mandatory and `aux_data` is optional

  - `<user id>` is a unique ID for a user. This is used for remembering the contents of previous interactions when the same user interacts with the application multiple times.

  - `<auxiliary data>` is used to send client status to the application. It is an JSON object and its contents are decided on an application-by-application basis.

  

####  After the session starts

JSON in the following form.

  ```json
  {
    "user_id": <user id: string>,
    "session_id": <session id: string>,
    "user_utterance": <user utterance string: string>,
    "aux_data": <auxiliary data: object (types of values are arbitrary)>
  }
  ```

  - `user_id`, `session_id`, and `user_utterance` are mandatory, and `aux_data` is optional.
  - `<session id>` is the session ID included in the responses.

  - `<user utterance string>` is the utterance made by the user.


### Response

  ```json
  {
    "session_id":<session id: string>,
    "system_utterance": <system utterance string: string>, 
    "user_id":<user id: string>, 
    "final": <end-of-dialogue flag: bool> 
    "aux_data": <auxiliary data: object (types of values are arbitrary)>
  }

  ```
  - `<session id>` is the ID of the dialog session. A new session ID is generated when new session starts.
  - `<system utterance string>` is the utterance of the system.
  - `<user id>` is the ID of the user sent in the request.
  - `<end-of-dialog flag>` is a boolean value indicating whether the dialog has ended or not.
  - `<auxiliary data>` is data that the application sends to the client. It is used to send
    information such as server status. 


## WebAPI

Applications can also be accessed via WebAPI.

### Server Startup


Set the PYTHONPATH environment variable.


```sh
export PYTHONPATH=<DialBB directory>:$PYTHONPATH
```

Start the server by specifying a configuration file.

```sh
python <DialBB directory>/run_server.py [--port <port>] <config file>
```

The default port number is 8080.


### Connection from Client (At the Start of a Session)

- URI

  ```
  http://<server>:<port>/init
  ```

- Request header

  ```
  Content-Type: application/json
  ```

- Request body

  The data is in the same JSON format as the request in the case of the class API.


- Response

  The data is in the same JSON format as the response in the case of the class API.
  
### Connection from Client (After the Session Started)


- URI

  ```
  http://<server>:<port>/dialogue
  ```

- request header

  ```
  Content-Type: application/json
  ```

- request body

  The data is in the JSON format as the request in the case of the class API.

- response

  The data is in the same JSON format as the response in the case of the class API.

(configuration)=
## Configuration

The configuration is data in dictionary format and is assumed to be provided with a yaml file.

Only the `blocks` element is required for configuration; the blocks element is a list of what each block specifies (this is called the block configuration) and has the following form

```
blocks:
  - <Block Configuration>
  - <Block Configuration>
  ...
  - <Block Configuration>
```

The following are the mandatory elements of each block configuration.

- `name` 

  Name of the block. Used in the log.

- `block_class`

  The class name of the block. This should be written as a realtive path from a module search path (an element of `sys.path`. Paths set to `PYTHONPATH` environment variable are included in it).


  The directory containing the configuration files is automatically registered in the path (an element of `sys.path`) where the module is searched.


  Built-in classes should be specified in the form `dialbb.built-in_blocks.<module name>.<class name>.` Relative paths from `dialbb.builtin_blocks` are also allowed, but are deprecated.

- `input`

  This defines the input from the main module to the block. It is a dictionary type data, where keys are used for references within the block and values are used for references in the blackboard (data stored in the main module). For example, if the following is in a block configuration, 
then what can be referenced by `input['sentence']` in the block is `blackboard['canonicalized_user_utterance']` in the main module.

  ```yaml
  input: 
    sentence: canonicalized_user_utterance
  ```

  If the specified key is not in the blackboard, the corresponding element of the input becomes `None`.

- `output`

  Like `input`, it is data of dictionary type, where keys are used for references within the block and values are used for references on the blackboard. If the following is specified:

  ```yaml
  output:
    output_text: system_utterance
  ```

  and if the output from the block is `output`, then the following process is performed.

  ```python
	blackboard['system_utterance'] = output['output_text']
  ```

  If `blackboard` already has `system_utterance` as a key, the value is overwritten.


## How to make your own blocks

Developers can create their own blocks.

The block class must be a descendant of `diabb.abstract_block.AbstractBlock`.


### Methods to be Implemented

- `__init__(self, *args)`
  
   Constructor. It is defined as follows:

   ```python
   def __init__(self, *args):
    
        super().__init__(*args)
    
        <Process unique to this block>
   ```

- `process(self, input: Dict[str, Any], session_id: str = False) -> Dict[str, Any]`

  Processes input and returns output. The relationship between input, output and the main module's
blackboard is defined by the configuration (see "{ref}`configuration`"). `session_id` is a string passed from the main module that is unique for each dialog session.


### Available Variables

- `self.config` (dictionary)

   This is a dictionary type data of the contents of the configuration. By referring to this data, it is possible to read in elements that have been added by the user.
   
- `self.block_config` (dictionary)

   The contents of the block configuration are dictionary type data. By referring to this data, it is possible to load elements that have been added independently.
   
- `self.name` (string)

   The name of the block as written in the configuration. 

- `self.config_dir` (string)

   The directory containing the configuration files. It is sometimes called the application directory.

### Available Methods

The following logging methods are available

- `log_debug(self, message: str, session_id: str="unknown")`

  
  Outputs debug-level logs to standard error output. `session_id` can be specified as a session ID to be included in the log.

- `log_info(self, message: str, session_id: str="unknown")`

  Outputs info level logs to standard error output.
  
- `log_warning(self, message: str, session_id: str="unknown")`

  Outputs warning-level logs to standard error output.

- `log_error(self, message: str, session_id: str="unknown")`

  Outputs error-level logs to standard error output.


## Debug Mode

When the environment variable `DIALBB_DEBUG` is set to `yes` (case-insensitive) during Python startup, the program runs in debug mode. In this case, the value of `dialbb.main.DEBUG` is `True`. This value can also be referenced in blocks created by the application developer.


If `dialbb.main.DEBUG` is `True`, the logging level is set to debug; otherwise it is set to info.

## Test Using Test Scenarios

The following commands can be used to test with test scenarios.

```sh
$ python dialbb/util/test.py <application configuration> \
  <test scenario> [--output <output file>]
```

The test scenario is a text file in the following format:

```
<session separation>
System: <system utterance>
User: <user utterance>
System: <system utterance>
User: <user utterance>
...
System: <system utterance>
User: <user utterance>
System: <system utterance>
<session separation>
<System: <system utterance>
User: <user utterance>
System: <system utterance>
User: <user utterance>
...
System: <system utterance>
User: <user utterance>
System: <system utterance>
<session separation>
...

```

`<session separation>` is a string stareging with `----init`.

The test script receives system utterance by inputting `<user speech>` to the application in turn. If the system utterances differ from the script's system utterances, a warning is issued. When the test is finished, the dialogues can be output in the same format as the test scenario, including the output system utterances. By comparing the test scenario with the output file, changes in responses can be examined.



