# Installing DialBB and Running the Sample Applications

This chapter describes how to install DialBB and run the sample applications. If you have any difficulty in performing the following tasks, please ask someone in the know.


## Execution Environment

We have confirmed that the following procedure works on python 3.8.10 and 3.9.12 on Ubuntu 20.04.

The following instructions assume that you are working with bash on Ubuntu. If you are using other shells or the Windows command prompt, please read the following instructions accordingly.

## Installing DialBB

Clone the source code from github.

```sh
$ git clone https://github.com/c4a-ri/dialbb.git
```

In this case, a directory named `dialbb` is created.

If you want to install in a directory with a specific name, do the following.

```sh
$ git clone https://github.com/c4a-ri/dialbb.git <directry name>

```

The resulting directory is referred to below as the <DialBB directory>.


## Installing Python libraries

- Go to <DialBB directory>.

- Next, build a virtual environment if necessary. The following is an example of venv.

  ```sh
  $ python -m venv venv  # Create a virtual environment named venv
  $ venv/bin/activate   # Enter the virtual environment
  ```

- Next, do the following to install the minimu set of libraries.


  ```python
  $ pip install -r requirements.txt 
  ```


## Parroting application

### Startup

It is an application that just parrots back and forth. No built-in block classes are used.

```sh
$ python run_server.py sample_apps/parrot/config.yml
```


### Operation Check


Execute the following on another terminal. If you do not have curl installed, test it using the method described in the "{ref}`test_with_browser`" section.


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

- Access after the second time

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

## SNIPS+Network-based Dialogue Management Application

DialBB has sample applications that uses only pre-created blocks (built-in blocks).

This is a sample application using the following built-in blocks.
The Japanese version is available in `sample_apps/network_en/` and the English version is available in `sample_apps/network_en/`.

- Japanese Language Applications

  - {ref}`japanese_canonicalizer`
  - {ref}`sudachi_tokenizer`
  - {ref}`snips_understander`
  - {ref}`stn_manager`

- English Application

  - {ref}`simple_canonicalizer`
  - {ref}`whitespace_tokenizer`
  - {ref}`snips_understander`
  - {ref}`stn_manager`

### Install required Python libraries

  If you do not use this application, you may skip the following steps.



  Do the following

  ```sh
  # Run one of the following
  $ pip install -r sample_apps/network_en/requirements.txt
  $ pip install -r sample_apps/network_en/requirements.txt

  # To create and use an English application
  $ python -m snips_nlu download en

  # To create and use a Japanese language application
  $ python -m snips_nlu download ja
  ```

Note:

 - You may be asked to install additional software, such as Rust, if an error occurs during the installation process. In that case, follow the instructions to install the software. If the installation does not work, please contact the contact person listed in the README.

  - For python3.9 and above, the following error may occur. 
  
    ```
	ModuleNotFoundError: No module named 'setuptools_rust'
    ```

     In this case, the following commands may solve the problem. 
	
	```
	pip install --upgrade pip setuptools wheel
    ```

     Install other necessary libraries according to the error messages. If you have any questions or
	problems, please contact us.
	


  - When running with Anaconda on Windows, Anaconda Prompt may need to be started in administrator
mode.

  - If you are using pyenv, you may get the following error

    ```
    ModuleNotFoundError: No module named '_bz2' 
    ```
    
    See [this page](https://stackoverflow.com/questions/60775172/pyenvs-python-is-missing-bzip2-module) and others for how to deal with this problem.


## Installing Graphviz

[Install Graphviz](https://graphviz.org/download/) by referring to the Graphviz website. However, it is possible to run the application without Graphviz.


### Startup

The following command starts the application.


  - English application

  ```sh
  $ python run_server.py sample_apps/network_en/config.yml 
  ```

  - Japanese application

  ```sh
  $ python run_server.py sample_apps/network_ja/config.yml 
  ```

(test_with_browser)=
### Operation Check

If the hostname or IP address of the server from which the application is launched is `<hostname>`, access the following URL from a browser, and a dialogue screen will appear.

```
http://<hostname>:8080 
```

If the server is running on Windows, the dialog screen may not appear in your browser. In this case, a simple dialog screen will appear when you connect to the following URL.

```
http://<hostname>:8080/test
```

### Operation Check Using Testset

The following commands can be used to test the sequential processing and interaction of user speech.

   ```sh
   $ python dialbb/util/test.py sample_apps/network_en/config.yml \
     sample_apps/network_en/test_inputs.txt --output \
     sample_apps/network_en/_test_outputs.txt
   ```

    The dialog exchange is written to `sample_apps/network_en/_test_outputs.txt`.
	
  - Japanese

   ```sh
   $ python dialbb/util/test.py sample_apps/network_ja/config.yml \
   sample_apps/network_ja/test_inputs.txt --output \
   sample_apps/network_ja/_test_outputs.txt
   ```

   The dialog exchange is written to `sample_apps/network_ja/_test_outputs.txt`.


## Experimental application

An experimental application is available at `sample_apps/lab_app_en/` (Japanese only). This application is used to test various functions of the built-in blocks. It uses the following built-in blocks.


- {ref}`japanese_canonicalizer`
- {ref}`sudachi_tokenizer`
- {ref}`snips_understander`
- {ref}`spacy_ner`
- {ref}`stn_manager`

### Installing Python libraries

  Do the following

  ```sh
  $ pip install -r sample_apps/lab_app_en/requirements.txt
  ```

### Setting environment variables

This application can use OpenAI's ChatGPT; to use ChatGPT, set the OpenAI API key in the environment variable `OPENAI_KEY`. The following is a bash example.

```sh
$ export OPENAI_KEY=<OpenAI's API key>.
  ```

If the environment variable `OPENAI_KEY` is not specified, it works without ChatGPT.



### How to Activate

  ```sh
  $ python run_server.py sample_apps/lab_app_en/config_en.yml
  ```

### Test Method

The following commands allow you to test features not used in {ref}`snips_network_app`.

  ```sh
  $ cd sample_apps/lab_app_en
  $ export DIALBB_HOME=<DialBB home directory>.
  $ export PYTHONPATH=$DIALBB_HOME:$PYTHONPATH
  $ python $DIALBB_HOME/dialbb/util/send_test_requests.py config.yml test_requests.json
  ```

(rename `send_test_request.py` to `send_test_requests.py` in ver. 0.6)

## Applications using ChatGPT

The following embedded blocks are used to interact with OpenAI's ChatGPT.

- {ref}`chatgpt_dialogue`


### Installing Python libraries

  Do the following

  ```sh
  $ pip install -r sample_apps/chatgpt/requirements.txt
  ```

### Setting environment variables

Set the environment variable OPENAI_KEY to the OpenAI API key. The following is a bash example.

```sh
$ export OPENAI_KEY=<OpenAI's API key>.
```



### How to Activate

  English version

  ```sh
  $ python run_server.py sample_apps/chatgpt/config_en.yml
  ```

  Japanese (language) version

  ```sh
  $ python run_server.py sample_apps/chatgpt/config_en.yml
  ```




