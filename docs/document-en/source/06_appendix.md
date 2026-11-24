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

(multi_party_dialogue)=

## Multi-party Dialogue

A hub relays utterances and membership changes over Socket.IO. Each participant connects through a client called a spoke. Humans use a terminal or GUI spoke, and each DialBB spoke runs its own application session and decides when to speak.

### Run the sample

Run the commands from the repository root with the same Python environment in every terminal. Install the multi-party dependencies with `python -m pip install -e ".[multi-party]"`. Set `OPENAI_API_KEY` in each DialBB spoke's environment or in the repository root's `.env` file. Set `model` in each sample configuration to an OpenAI model available to your account if needed.

To launch the hub, John, Paul, and Lisa's GUI together, run `sample_apps\multi_party_en\test.bat` on Windows or `sh sample_apps/multi_party_en/test.sh` on Linux or macOS. The launchers require `curl` to check that the hub is ready. Pass `--cli` to use a terminal for Lisa, `--all-bots` to run Lisa as DialBB, or `--port 5001` to use another port.

To start the processes individually, start the hub first, then start John and Paul. Run each command in a separate terminal.

```sh
python -m dialbb.lib.multi_party.hub
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config1.yml John
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config2.yml Paul
```

John opens the conversation about favorite foods when he joins. To join as Lisa, run one of the following commands in another terminal.

```sh
python -m dialbb.lib.multi_party.user_spoke_gui Lisa
python -m dialbb.lib.multi_party.user_spoke Lisa
```

In the GUI, click **Join**, then click **Send** or press Ctrl+Enter to send. Enter is available for IME input. In the terminal, press Enter to join, then press Enter after typing each utterance. To run Lisa as a third DialBB participant, use this command in place of the human spoke.

```sh
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config3.yml Lisa
```

Use Ctrl+C to stop a command-line process, or close the human spoke's GUI window.

### Hub and Socket.IO protocol

The hub hosts one conversation. Its default address is `localhost:5000`. Use `--host` and `--port` to change the listening address. Each spoke accepts `--hub-url` and defaults to `http://localhost:5000`. For example, if the hub runs with `--port 5001`, append `--hub-url http://localhost:5001` to each spoke command.

Each connection registers with `join` before it can send or receive conversation events. Names are case-sensitive, must contain a non-whitespace character, and must be unique among joined participants. Whitespace around names is preserved. Repeating `join` on the same connection with the same name succeeds without emitting another notification. To join under a different name, open a new connection.

| Event sent to the hub | Payload | Effect |
| --- | --- | --- |
| `join` | `{"speaker": "Lisa"}` | Registers the connection. |
| `utterance` | `{"speaker": "Lisa", "utterance": "I like ramen."}` | Relays the text as sent. The speaker must match the registered name and the text must contain a non-whitespace character. |

Both events acknowledge success with `{"ok": true}` or return `{"error": "..."}` on failure. Disconnecting removes the participant.

| Event broadcast by the hub | Payload fields | Recipients |
| --- | --- | --- |
| `participant_joined` | `speaker`, `participants` | All joined participants, including the new participant. |
| `broadcast_utterance` | `speaker`, `utterance`, `participants` | All joined participants, including the speaker. |
| `participant_left` | `speaker`, `participants` | All remaining participants. |

`participants` lists the names registered at the time of the event. The hub has no authentication or history replay. Late arrivals receive events from their own join onward. The spokes have automatic reconnection disabled. Restart a spoke to rejoin.

### DialBB spoke

The DialBB spoke takes `config_file` and `my_name` as positional arguments. It connects to the hub, starts a DialBB session with `initial=True`, `user_id: my_name`, and an empty `aux_data.participants` list, then registers with the hub and publishes any initial utterance. A single worker processes queued events in the same session. Each request includes the event's participant list as `aux_data.participants`.

| Event | `user_id` | `user_utterance` |
| --- | --- | --- |
| Another participant speaks | Speaker name | The utterance text |
| A participant joins | Joining participant's name | `(joined the conversaion)` |
| A participant leaves | Departing participant's name | `(left the conversaion)` |
| The spoke's silence timer expires | Empty string | `(silence)` |

The spelling `conversaion` is part of the protocol. The spoke passes its own join notification to DialBB and skips its own utterance broadcasts when processing dialogue. It sends any nonempty `system_utterance` to the hub using `my_name` as the speaker. A processing error disconnects the spoke.

#### Silence timer

Set `silence_timeout` in seconds at the top level of the application configuration, alongside `blocks`. Use a finite, nonnegative number. Omit it or set it to `0` to disable the timer. Once the spoke has joined, the timer resets on every received utterance, including its own, and continues running through joins and departures. On expiry, it sends a local `(silence)` request with the latest participant list. Queued events take priority, and the next timeout starts after the silence request finishes. Each spoke runs its own timer, so multiple spokes may speak at the same time.

(llm_dialogue_multi_party)=

### The `llm_dialogue` block's `multi_party` setting

Place `multi_party` under the {ref}`llm_dialogue` block in the application configuration. A mapping, including `{}`, enables multi-party mode. Omit the key or use `false` to disable it. The legacy value `true` enables the mode and reads the options from the block itself. Set `system_name` to match the spoke's `my_name` exactly so the block can identify itself in the participant list.

```yaml
language: en
silence_timeout: 10
blocks:
  - name: llm_dialogue
    block_class: dialbb.builtin_blocks.llm_dialogue.LLMDialogue
    input:
      dialogue_history: dialogue_history
      aux_data: aux_data
    output:
      system_utterance: system_utterance
      aux_data: aux_data
      final: final
    system_name: John
    first_system_utterance: Let's talk about our favorite foods.
    prompt_template: prompt_template1.txt
    model: openai:gpt-4.1-mini
    multi_party:
      silence: SILENT
      turn_taking_strategy: after_all_other_speak
      required_participants: [John, Lisa]
```

| Option | Default | Behavior |
| --- | --- | --- |
| `required_participants` | `[]` | List of participant IDs that must be present before the block returns `first_system_utterance`. With an empty list, it returns the initial utterance during initialization. It does this once per session. |
| `turn_taking_strategy` | Unset | `after_all_other_speak` waits for at least one utterance from every other current participant and waits if there are no others. `wait_n_turns` waits for the specified number of utterances from others, including multiple utterances from the same speaker. When unset, any nonempty input, including a join or leave notification, can trigger a response. |
| `turns_to_wait` | `1` | Positive integer used by `wait_n_turns`. |
| `silence` | Unset | Response text that the block converts to an empty utterance. The comparison strips surrounding whitespace and `「」` from the response. In the sample, the prompt tells the model to return `SILENT` when it chooses to wait. |

Both strategies count utterances since the block's last nonempty utterance and exclude join, leave, and silence notifications. A join or departure can trigger a response if the condition is already met. An empty response keeps the accumulated count. After the initial utterance, a truthy `aux_data.no_response_required` suppresses responses. Otherwise, a silence request bypasses the normal turn-taking wait and prompts the LLM to resume the conversation. Before the initial utterance, the required-participant check still applies.

The block uses the current `aux_data.participants` for turn-taking, falling back to the latest list in the dialogue history when the field is absent. An explicitly empty list means there are no participants. In the history passed to the LLM, it uses `user_id` for other speakers and `system_name` for its own utterances. If the current request includes `aux_data.participants`, the template can reference it as `{participants}`.

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
