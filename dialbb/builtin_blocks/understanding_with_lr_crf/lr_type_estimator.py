#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# lr_type_estimator.py
#   estimate type using logistic regression

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from pprint import pprint
from typing import List, Dict, Any, Tuple

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression


class LRTypeEstimator:

    def __init__(self, training_data: List[Dict[str, Any]]) -> None:
        """
        train crf model
        :param training_data:
        {"type": <type string>, "slots": <dict from slot names to slot values>, "example": <utterance string>,
         "tokens_with_pos": <list of tuples each of which consists of a token string and a POS string>}
        """

        self._vectorizer = CountVectorizer()
        labels: List[int] = []   # list of labels in integers
        self._id2label: Dict[int, str] = {}  # map from string labels to integers
        self._label2id: Dict[str, int] = {}  # map from integer id's to string labels
        i = 0

        training_texts: List[str] = []   # ["it will be sunny tomorrow", "it will rain tomorrow", ...]
        for item in training_data:
            text: str = " ".join([t[0] for t in item["tokens_with_pos"]])
            training_texts.append(text)
            label = item['type']

            label_id: int = self._label2id.get(label)
            if label_id is None:
                self._id2label[i] = label
                self._label2id[label] = i
                labels.append(i)
                i += 1
            else:
                labels.append(label_id)

        X_train = self._vectorizer.fit_transform(training_texts)
        y_train = np.array(labels)

        self._model = LogisticRegression()
        self._model.fit(X_train, y_train)   # train model

    def estimate_type(self, tokens_with_pos: List[Tuple[str, str]]) -> Tuple[List[str], List[Tuple[str, Any]]]:
        """
        estimate type of token set
        :param tokens: list of tuples consisting of token and its POS
        :return: - list of candidates of types
                 - dict from type to probability
        """

        # get vector
        tokens = [item[0] for item in tokens_with_pos]
        tokenized_input: str = " ".join(tokens)
        sentence_vector = self._vectorizer.transform([tokenized_input])

        # estimate type
        probabilities = self._model.predict_proba(sentence_vector)  # predict
        prob_distribution = []  # [(label, prob), (label, prob) ...]
        for i, prob in enumerate(probabilities[0]):
            prob_distribution.append((self._id2label[i], prob))
        # sort in descending order of prob
        prob_distribution = sorted(prob_distribution, key=lambda x: x[1], reverse=True)
        types: List[str] = [prob[0] for prob in prob_distribution]  # get list of labels
        return types, prob_distribution









