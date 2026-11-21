# DialBB multi-party conversation sample

This is the English version of [multi_party_ja](../multi_party_ja/README.md).
John, Paul, and Lisa chat about their favorite foods. John and Paul
are DialBB applications; Lisa can be either a human or another DialBB application.
Each application generates responses using the `LLMDialogue` block. A shared hub
broadcasts utterances and participant joins and departures.

## Installation

Use Python 3.11 or later. Run all commands below from the repository root,
using the same Python environment in each terminal.

```sh
python -m pip install -e ".[multi-party]"
```

If DialBB is already installed, install the additional dependencies with:

```sh
python -m pip install -r sample_apps/multi_party_en/requirements.txt
```

## Start the conversation

Start the hub in its own terminal:

```sh
python -m dialbb.lib.multi_party.hub
```

In each terminal running a DialBB participant, set the API key for its model.
For OpenAI models, use the following in PowerShell:

```powershell
$env:OPENAI_API_KEY = "<OpenAI API Key>"
```

In bash/zsh, use `export OPENAI_API_KEY="<OpenAI API Key>"`.
You can also set `OPENAI_API_KEY=...` in the repository root's `.env` file.

Start John and Paul in separate terminals:

```sh
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config1.yml John
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config2.yml Paul
```

John sends "Let's talk about our favorite foods." when he joins.
Paul waits for John and Lisa before completing his initial waiting phase.
When Lisa runs as a DialBB spoke, she waits for John and Paul before completing hers.
Paul and the DialBB version of Lisa both have empty initial utterances.
Participants joining later do not receive earlier utterances.

To join as Lisa, open another terminal and choose either the GUI or the CLI:

```sh
python -m dialbb.lib.multi_party.user_spoke_gui Lisa
```

In the GUI, click Join, type in the input field, and click Send or press Ctrl+Enter.
Enter alone does not send a message, allowing IME composition and confirmation.

```sh
python -m dialbb.lib.multi_party.user_spoke Lisa
```

In the CLI, press Enter to join, then type an utterance and press Enter to send it.

To run all three participants as DialBB applications, replace the human participant
with the following command in a terminal with the API key set:

```sh
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config3.yml Lisa
```

## Configuration and behavior

The configurations preserve the models and turn-taking settings of the Japanese
sample. Change `model` in each configuration as needed. Other model providers may
require their own API keys and LangChain integration packages.

| Participant | Configuration | Turn-taking strategy | Silence timeout |
| --- | --- | --- | --- |
| John | `config1.yml` | Wait for all other current participants to speak | 5 seconds |
| Paul | `config2.yml` | Wait for two utterances | 12 seconds |
| Lisa (DialBB) | `config3.yml` | Wait for one utterance | Disabled |

- Each prompt defines the participant's persona and requests English responses.
  The prompt and `multi_party.silence` both use `SILENT` for choosing not to speak;
  this response is converted to an empty utterance and is not broadcast.
- `multi_party.required_participants` delays the initial utterance until all listed
  user IDs are present. Participant names are case-sensitive; use the names shown
  in the commands so they match `system_name` and the required participant lists.
- Joining and leaving do not count toward the turn-taking utterance count.
- `silence_timeout` belongs at the top level, alongside `blocks`. An omitted value
  or `0` disables it. After the timeout without received speech, the spoke sends
  `user_id: ""` and `user_utterance: "(silence)"` to its own DialBB session.
  This asks the LLM to resume the conversation without the usual turn-taking wait.
  Waiting for required participants still takes priority.
- Receiving any utterance, including the spoke's own broadcast, resets its timer.
  Joining and leaving do not reset it. Requests are processed sequentially, and
  another silence timeout is scheduled after the silence response completes.
- Timers operate independently for each spoke, so simultaneous responses are possible.
- Every event includes the current participant IDs in `aux_data.participants`.
  Join and leave notifications use `"(joined the conversaion)"` and
  `"(left the conversaion)"` respectively. These spellings are part of the protocol.
- A DialBB processing error disconnects that participant from the hub.
  The other participants receive a departure notification.
- To change the port, start the hub with `--port 5001` and append
  `--hub-url http://localhost:5001` to each participant command.
- Stop terminal participants with Ctrl+C, or close the GUI window.
  Restart a spoke to rejoin. Participant names must be unique among connected participants.

## Windows launcher

After setting the API key in the environment or the root `.env`, run:

```bat
sample_apps\multi_party_en\test.bat
```

This opens four consoles for the hub, John, Paul, and Lisa, plus Lisa's
GUI window. Use the GUI to join and send messages; Lisa's console displays logs.

Use the CLI for the human participant, run all three as bots, or change the port:

```bat
sample_apps\multi_party_en\test.bat --cli
sample_apps\multi_party_en\test.bat --all-bots
sample_apps\multi_party_en\test.bat --port 5001
```

The batch file directly starts the hub and participants; no Python launcher script is used.
It requires `curl.exe` (included in recent Windows versions) to check that the
hub is ready before opening participant consoles.
It uses `.venv\Scripts\python.exe` if present, otherwise `python`.
Set `DIALBB_PYTHON` to an executable path to select another Python environment.

See the [multi-party module specification](../../dialbb/lib/multi_party/README.md)
for the full protocol and DialBB integration behavior.

## Shell launcher (Linux/macOS)

Use a POSIX shell with `curl` installed:

```sh
sh sample_apps/multi_party_en/test.sh
sh sample_apps/multi_party_en/test.sh --cli
sh sample_apps/multi_party_en/test.sh --all-bots
sh sample_apps/multi_party_en/test.sh --port 5001
```

The shell script starts the hub and bots in the background, then runs the human
GUI or CLI in the foreground. It prints the temporary directory containing the
hub and bot logs. Closing the human participant or pressing Ctrl+C stops the
processes started by the script. In all-bot mode, use Ctrl+C to stop.
Logs are kept for inspection.

The script uses `.venv/bin/python` if available, otherwise `python3`.
Set `DIALBB_PYTHON` to override the executable. Both launchers can be called from
any working directory. Python is still required to run DialBB itself; all launch
control is implemented in the bat/sh files.
