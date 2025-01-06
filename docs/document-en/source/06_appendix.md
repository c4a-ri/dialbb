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

## Discontinued Features

### Snips Understander Built-in Block

As Snips has become challenging to install with Python 3.9 and above, it was discontinued in version 0.9. Please use the LR-CRF Understander built-in block as an alternative.

### Whitespace Tokenizer and Sudachi Tokenizer Built-in Blocks

These blocks were discontinued in version 0.9. If you use LR-CRF Understander or ChatGPT Understander, there is no need for the Tokenizer blocks.

### Snips+STN Sample Application

This sample application was discontinued in version 0.9.

