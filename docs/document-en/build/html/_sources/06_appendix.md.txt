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

## Discontinued Features

### Snips Understander Built-in Block

As Snips has become challenging to install with Python 3.9 and above, it was discontinued in version 0.9. Please use the LR-CRF Understander built-in block as an alternative.

### Whitespace Tokenizer and Sudachi Tokenizer Built-in Blocks

These blocks were discontinued in version 0.9. If you use LR-CRF Understander or ChatGPT Understander, there is no need for the Tokenizer blocks.

### Snips+STN Sample Application

This sample application was discontinued in version 0.9.

