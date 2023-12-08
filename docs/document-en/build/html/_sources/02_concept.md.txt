# DialBB Overview

As mentioned in the introduction, DialBB is a framework for building dialogue systems.

A framework does not stand alone as an application, but forms an application by providing data and additional programs.

The basic architecture of a DialBB application is shown below.

![dialbb-arch](../../images/dialbb-arch-en.jpg)

The main module creates and returns a system utterance by making modules called blocks sequentially
process the data (including user utterances) inputted at each turn of the dialog. The inputted is data copied to data called blackboard [^fn] in the main block. Each block takes some of the elements of the blackboard and returns data in
dictionary format. The returned data is added to blackboard. If an element with the same key already exists in blackboard, it is overwritten. 

The type of block to be used is specified in the configuration file. Blocks can be either blocks provided by DialBB (built-in blocks) or blocks created by the application developer.

The configuration file also specifies what data the main module sends to and receives from each block. 

Details are explained in the "{ref}`framework`" section.


[^fn]: Before ver. 0.2, it was called payload. 
