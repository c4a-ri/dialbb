# [DialBB](https://c4a-ri.github.io/dialbb/): A Framework for Building Dialogue Systems

ver. 2.0.0

[<img src="./docs/images/japan_national_flag.jpg" width="5%">日本語](README-ja.md)

## Project Main Page

Please refer to [the project main page](https://c4a-ri.github.io/dialbb/), which includes the overview of DialBB and the links to the documents.

## Documents

Please refer to the [document](https://c4a-ri.github.io/dialbb/document-en/build/html/) for detailed specification and the way of application development. 

## Citation

Please cite the following paper when publishing a paper on work that uses DialBB.

- Mikio Nakano and Kazunori Komatani. [DialBB: A Dialogue System Development Framework as an Educational Material](https://aclanthology.org/2024.sigdial-1.56). In Proceedings of the 25th Annual Meeting of the Special Interest Group on Discourse and Dialogue (SIGDIAL-24), pages 664–668, Kyoto, Japan. Association for Computational Linguistics, 2024

## License

DialBB is released under Apache License 2.0.

## Getting Started

### Execution Environment

We have confirmed that the following procedure works on Python 3.10.13 on Ubuntu 20.04/Windows 11.  We haven't heard that application dosn't work with Python 3.10-3.13 and on Windows 11 and MacOS (including Apple Silicon), though we haven't completely confirmed. 

The following instructions assume that you are working with bash on Ubuntu. If you are using other shells or the Windows command prompt, please read the following instructions accordingly.

### Installing DialBB

- Build a virtual environment if necessary. The following is an example of venv.

  ```sh
  $ python -m venv venv  # Create a virtual environment named venv
  $ venv/bin/activate   # Enter the virtual environment
  ```

- Download `dialbb-*-py3-none-any.whl` file from [distribution directory](dist).

- Execute the following.

  ```sh
  $ pip install <downloaded whl file>
  ```

### Download the Sample Applications

Download the sample applications file at [docs/files/sample_apps.zip](docs/files/sample_apps.zip) and extract them in an appropriate directory.


### Running the Parroting Application

It is an application that just parrots back and forth. No built-in block classes are used.

#### Startup

```sh
$ dialbb-server sample_apps/parrot/config.yml
```


#### Operation Check on Terminal


Execute the following on another terminal. If you do not have curl installed, test it from a browser as described later.


- First access

  ```sh
  $ curl -X POST -H "Content-Type: application/json" \
    -d '{"user_id":"user1"}' http://localhost:8080/init
  ```
   The following response will be returned.

  ```json
  {"aux_data":null, 
   "session_id":"dialbb_session1", 
   "system_utterance":"I'm a parrot. You can say anything.", 
   "user_id":"user1"}
  ```

- Second access or later

  ```sh
  $ curl -X POST -H "Content-Type: application/json" \
    -d '{"user_utterance": "Hello", "user_id":"user1", "session_id":"dialbb_session1"}' \
    http://localhost:8080/dialogue
  ```

   The following response will be returned.

  ```json
  {"aux_data":null,
   "final":false,
   "session_id":"dialbb_session1",
   "system_utterance":"You said \"Hello\"",
   "user_id":"user1"}
  ```

#### Operation Check Using a Browser

If the hostname or IP address of the server from which the application is launched is `<hostname>`, access the following URL from a browser, and a dialogue screen will appear.

```
http://<hostname>:8080 
```

If the server is running on Windows 10, the dialog screen may not appear in your browser. In this case, a simple dialog screen will appear when you connect to the following URL.

```
http://<hostname>:8080/test
```

### LLM Dialogue Applications

This application uses single prompt template for an LLM (Large Language Model) to engage in dialogues. 

Only the following builtin block is used.

- LLM Dialogue Block


#### Setting environment variables

This application uses OpenAI's ChatGPT by default. So, set the OpenAI API key in the environment variable `OPENAI_API_KEY`. The following is a bash example. 

```sh
$ export OPENAI_API_KEY=<OpenAI's API key>.
```

You can also write the key in `.env`  in the working directory as follows:

```
OPENAI_API_KEY=<OpenAI's API key>
```

You can also use other LLMs by modifiying the configuration files. In that case, set necessary keys in the enviroment variables or specify them in `.env`.

#### Startup

  English version:

  ```sh
$ dialbb-server sample_apps/llm_dialogue/config_en.yml
  ```

  Japanese version:

  ```sh
$ dialbb-server sample_apps/llm_dialogue/config_en.yml
  ```


### DST+STN Applications

Sample applications using DST (dialogue state tracking) and STN (State-transition network) are available at `sample_apps/dst_stn_ja/` (Japanese) and `sample_apps/dst_stn_en/` (English) . These applications are used to test various functions of the built-in blocks. They use the following built-in blocks.


- DST with LLM Block
- STN Manager Block

#### Installing Graphviz

Install Graphviz by referring to the [Graphviz website](https://graphviz.org/). However, Graphviz is **not necessary** to run the application.

#### Setting environment variables

These application also use OpenAI's ChatGPT. In the same way as LLM Dialogue Applications, set the OpenAI's API key to the environment variable.

#### Startup

  ```sh
  $ dialbb-server sample_apps/dst_stn_en/config.yml # English app
  $ dialbb-server sample_apps/dst_stn_ja/config.yml # Japanese app
  ```

#### Test Method

The following commands allow you to test various features.

  ```sh
  $ dialbb-send-test-requests sample_apps/dst_stn_ja/config.yml test_requests.json # for English app
  $ dialbb-send-test-requests sample_apps/dst_stn_ja/config.yml test_requests.json # for Japanese app
  ```

### Uninstalling DialBB

Do the following

```sh
$ dialbb-uninstall
$ pip uninstall -y dialbb
```

## Requests, Questions, and Bug Reports

Please feel free to send your requests, questions, and bug reports about DialBB to the following. Even if it is a trivial or vague question, feel free to send it.

- Report bugs, point out missing documentation, etc.: [GitHub Issues](https://github.com/c4a-ri/dialbb/issues)

- Long-term development policy, etc.: [GitHub Discussions](https://github.com/c4a-ri/dialbb/discussions)

- Anything: email at `dialbb at c4a.jp`


## Copyright

(c) C4A Research Institute, Inc.
