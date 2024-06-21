#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# crf_slot_extractor.py
#   extract slot using CRF

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

from typing import List, Dict, Any, Tuple

class CRFSlotExtractor:

    def __init__(self, training_data: List[Dict[str, Any]]) -> None:
        """
        train crf model
        :param training_data:
        {"type": <type string>, "slots": <dict from slot names to slot values>, "example": <utterance string>,
         "tokens_with_pos": <list of tuples each of which consists of a token string and a POS string>}
        """


        crf_X_train = []
        crf_y_train = []

        for sample in training_data:

            crf_features: List[Dict[str, Any]] = self._tokens_with_pos2crf_features(tokens_with_pos)
            crf_labels: List[str] = self._get_crf_labels(tokens_with_pos, sample['slots'])
            crf_X_train.append(crf_features)
            crf_y_train.append(crf_labels)

        self.crf = sklearn_crfsuite.CRF(
            algorithm='lbfgs',
            c1=0.1,
            c2=0.1,
            max_iterations=100,
            all_possible_transitions=True
        )

        self.crf.fit(crf_X_train, crf_y_train)


    def _tokens_with_pos2crf_features(self, tokens_with_pos: List[Tuple[str, str]]):
        return [self._word2features(tokens_with_pos, i) for i in range(len(tokens_with_pos))]


    def _get_crf_labels(self, tokens_with_pos: List[Tuple[str, str]], slots: Dict[str, str]) -> List[str]:

        crf_labels: List[str] = ['O'] * len(tokens_with_pos)  # crf labels for each token
        for slot_name, slot_value in slots.items():
            str_to_search: str = slot_value
            b_index: int = -1
            i_indices: List[int] = []
            for i, (token, pos) in enumerate(tokens_with_pos):
                if str_to_search.startswith(token):
                    if crf_labels[i] != 'O': # already in another slot
                        b_index = -1  # ignore this slot
                        continue
                    if b_index < 0:
                        b_index = i  # start of the slot
                    else:
                        i_indices.append(i)  # to label I-...
                    if str_to_search == token:  # end of slot
                        break
                    else:
                        str_to_search = str_to_search[len(token):] # remove the first token part
                        if str_to_search.startswith(' '):  # especially for English
                            str_to_search = str_to_search[1:]  # remove whitespace
            if b_index >= 0:  # slot found
                crf_labels[b_index] = 'B-' + slot_name
                for j in i_indices:
                    crf_labels[b_index] = 'I-' + slot_name

        return crf_labels


    def extract_slots(self, tokens_with_pos: List[Tuple[str, str]]) -> Dict[str, str]:
        """
        extracts slots
        :param tokens_with_pos: a list of tuples of tokens and pos labels
        :return: slot name-value dict {<slot name>: <slot value>, <slot name>: <slot value>, ...}
        """

        crf_features: List[Dict[str, Any]] = self._tokens_with_pos2crf_features(tokens_with_pos)
        predicted_labels: List[str] = self.crf.predict_single(crf_features)
        result: Dict[str, str] = {}
        slot_name: str = ""
        slot_value: str = ""
        for i in range(len(tokens_with_pos)):
            if predicted_labels[i].startswith("B-"):
                slot_name = predicted_labels[i].replace("B-", "")
                slot_value = tokens_with_pos[i][0]
            elif predicted_labels[i].startswith("I-") \
                and slot_name == predicted_labels[i].replace("I-", ""):
                    if self._language == 'ja':
                        slot_value += tokens_with_pos[i][0]
                    elif self._language == 'en':
                        slot_value += ' ' + tokens_with_pos[i][0]
            else:  # label is O or different I
                if slot_name:
                    result[slot_name] = slot_value
                slot_name = ""
                slot_value = ""
        if slot_name:
            result[slot_name] = slot_value
        return result
