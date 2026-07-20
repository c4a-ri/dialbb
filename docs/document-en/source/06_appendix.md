# Appendix

## Frontend

DialBB comes with two sample frontends for accessing the Web API.

### Simple Frontend

You can access it at the following URL.

```text
http://<host>:<port>
```

This frontend displays system and user utterances as speech bubbles.

It cannot send `aux_data`, and it does not display response fields other than the system utterance.

### Debug Frontend

You can access it at the following URL.

```text
http://<host>:<port>/test
```

This frontend displays system and user utterances in a list format.

It can send `aux_data`, and it also displays the `aux_data` included in the response.

## How to Modify DialBB Source Code

Clone the GitHub repository. Let the cloned directory be `<DialBB directory>`.

```sh
git clone git@github.com:c4a-ri/dialbb.git <DialBB directory>
```

Install the dependencies with `uv`. This also installs DialBB in editable mode, so changes to the source code are reflected immediately.

```sh
cd <DialBB directory>
uv sync
```

When starting DialBB, run it with `uv run`.

```sh
uv run dialbb-server [--port <port>] <config file>
```

You can also start it by specifying the Python file directly. This is useful when using an IDE such as PyCharm or VS Code.

```sh
uv run python <DialBB directory>/run_server.py [--port <port>] <config file>
```

## Discontinued Features

### Snips Understander Built-in Block

Snips was discontinued in version 0.9 because it is difficult to install on Python 3.9 and later. Use the LR-CRF Understander built-in block instead.

### Whitespace Tokenizer and Sudachi Tokenizer Built-in Blocks

These blocks were discontinued in version 0.9. If you use the LR-CRF Understander or ChatGPT Understander, you do not need a tokenizer block.

### Snips+STN Sample Application

This sample application was discontinued in version 0.9.

### Simple Application

This sample application was discontinued in version 2.0.

### Experimental Application

This sample application was discontinued in version 2.0.