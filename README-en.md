# DialBB: A Framework for Building Dialogue Systems

ver.0.6.0

DialBB is a framework for building dialogue systems.

This software is released for non-commercial use. For details of the license, please see [License](LICENSE-en).

Refer to the [document](https://c4a-ri.github.io/dialbb/document-en/build/html/) for details and installation instructions. Documentation for other than the latest version can be found in the [Links](https://c4a-ri.github.io/dialbb/) section.

## Overview

The main module of DialBB application recives a user utterance input in JSON format via method calls or via the Web API returns a system utterance in JSON format.


The main module works by calling several submodules, called blocks, in sequence.

Each block takes JSON format (data in Python dict) and returns the data in JSON format.


The class and input/output of each block are specified in the configuration file for
each application.


![dialbb-arch-en](docs/images/dialbb-arch-en.jpg)

## Reqeusts, Questions, and Bug Rerpots

Please feel free to send your requests, questions, and bug reports about DialBB to the following
address. Even if it is a trivial or vague question, feel free to send it.


- Report bugs, point out missing documentation, etc.: [GitHub Issues](https://github.com/c4a-ri/dialbb/issues)

- Long-term development policy, etc.: [GitHub Discussions](https://github.com/c4a-ri/dialbb/discussions)

- Anything: `dialbb at c4a.jp`

(c) C4A Research Institute, Inc.


