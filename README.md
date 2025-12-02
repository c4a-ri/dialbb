# [DialBB](https://c4a-ri.github.io/dialbb/): A Framework for Building Dialogue Systems

ver. 1.1.3

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

We have confirmed that the following procedure works on Python 3.10.13 on Ubuntu 20.04.  We haven't heard that application dosn't work with Python 3.9 or later and on Windows10/11 and MacOS (including Apple Silicon), though we haven't completely confirmed. 

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

Download the sample applications file by clicking [https://c4a-ri.github.io/dialbb/files/sample_apps.zip](https://c4a-ri.github.io/dialbb/files/sample_apps.zip) and extract them in an appropriate directory.


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

### Simple Applications

This is a sample application using the following built-in blocks. The English version is available in `sample_apps/simple_en/` and the Japanese version is available in `sample_apps/simple_ja/`.

- English Application

  - Simple Canonicalizer Block
  - LR-CRF Understander Block (language understanding based on Logistic Regression and Conditional Random Fields)
  - STN Manager Block (state transition network-based dialogue manager)
- Japanese Application

  - Japanese Canonicalizer Block
  - LR-CRF Understander  Block
  - STN Manager  Block


#### Installing Graphviz

Install Graphviz by referring to the [Graphviz website](https://graphviz.org/). However, Graphviz is **not necessary** to run the application.


#### Startup

The following command starts the application.


  - English application

    ```sh
    $ dialbb-server sample_apps/simple_en/config.yml 
    ```


  - Japanese application

    ```sh
    $ dialbb-server sample_apps/simple_ja/config.yml 
    ```

#### Operation Check

Operation check can be done with a browser. (See "Running the Parroting Application" above.)

#### Operation Check Using Test Sets

The following commands can be used to test the sequential processing and interaction of user speech.

- English

  ```sh
  $ dialbb-test sample_apps/simple_en/config.yml \
    sample_apps/simple_en/test_inputs.txt --output \
    sample_apps/simple_en/_test_outputs.txt
  ```

​	The dialog exchange is written to `sample_apps/simple_en/_test_outputs.txt`.

  - Japanese

    ```sh
    $ diabb-test sample_apps/simple_ja/config.yml \
      sample_apps/simple_ja/test_inputs.txt --output \
      sample_apps/simple_ja/_test_outputs.txt
    ```

​       The dialog exchange is written to `sample_apps/simple_ja/_test_outputs.txt`.


### Experimental Applications

Experimental applications are available at `sample_apps/lab_app_ja/` (Japanese) and `sample_apps/lab_app_en/` (English) . This application is used to test various functions of the built-in blocks. It uses the following built-in blocks.


- English Application

  - Simple Canonicalizer Block
  - ChatGPT Understander Block
  - ChatGPT NER Block
  - STN Manager Block

- Japanese Application

  - Japanese Canonicalizer Block
  - ChatGPT Understander Block
  - ChatGPT NER Block
  - STN Manager Block

#### Setting environment variables

This application uses OpenAI's ChatGPT. So, set the OpenAI API key in the environment variable `OPENAI_API_KEY`. The following is a bash example.

```sh
$ export OPENAI_API_KEY=<OpenAI's API key>.
```

#### Startup

  ```sh
  $ dialbb-server sample_apps/lab_app_en/config_en.yml # English app
  $ dialbb-server sample_apps/lab_app_en/config_ja.yml # Japanese app
  ```

#### Test Method

The following commands allow you to test features not used in the Simple Application.

  ```sh
  $ cd sample_apps/lab_app_en # in the case of English app
  $ cd sample_apps/lab_app_ja # in the case of Japanese app
  $ dialbb-send-test-requests config.yml test_requests.json
  ```

### ChatGPT Dialogue Application

This application uses only  OpenAI's ChatGPT to engage in dialogues. 

Only the following builtin block is used.

- ChatGPT Dialogue Block


#### Installing Python libraries

  Do the following

  ```sh
  $ pip install -r sample_apps/chatgpt/requirements.txt
  ```

#### Setting environment variables

Set the environment variable OPENAI_API_KEY to the OpenAI API key. The following is a bash example.

```sh
$ export OPENAI_API_KEY=<OpenAI's API key>.
```

#### Startup

  English version:

  ```sh
  $ dialbb-server sample_apps/chatgpt/config_en.yml
  ```

  Japanese version:

  ```sh
  $ dialbb-server sample_apps/chatgpt/config_en.yml
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
