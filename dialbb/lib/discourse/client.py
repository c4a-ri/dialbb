#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# client.py
#   dialbb-based discourse client
#
import argparse
import time
from typing import Dict, Any, List
import os
import yaml
import requests

from dialbb.main import DialogueProcessor

DEBUG: bool = True


discourse_url = os.getenv("DISCOURSE_URL")
topic_id = os.getenv("DISCOURSE_TOPIC_ID")
discourse_api_key = os.getenv("DISCOURSE_API_KEY")
discourse_username = os.getenv("DISCOURSE_USERNAME")

INTERVAL: float = 10.0

participants = []
read_post_ids = []


def post_in_topic(message: str, topic_id: str):
    api_url = discourse_url + "posts.json/"
    theData = {
        'raw' :message,
        'topic_id' : topic_id
    }
    theHeaders = {
        'Api-Key': discourse_api_key,
        'Api-Username': discourse_username
    }
    res = requests.post(api_url, theData, headers=theHeaders)
    res = res.json()
    while "error" in res.keys():
        if res['error_type'] == 'rate_limit':
            print("rate_limit, wait 120 sec")
            time.sleep(120)
            res = requests.post(api_url, theData, headers=theHeaders)
            res = res.json()
            print("create_post: ", res)
    return res


def read_post_id_list(topic_id: str) -> None:

    global read_post_ids

    url = f"{discourse_url}/t/-/{topic_id}.json"
    res = requests.get(url)
    res = res.json()
    for post_id in res['post_stream']['stream']:
        read_post_ids.append(post_id)

    if DEBUG:
        print("read post are: " + str(read_post_ids))


def get_new_posts_in_topic(topic_id: str) -> List[Dict[str, Any]]:

    global read_post_ids

    result = []
    url = f"{discourse_url}/t/-/{topic_id}.json"
    res = requests.get(url)
    res = res.json()
    stream = res['post_stream']['stream']
    for id in stream:
        if id not in read_post_ids:
            url_to_get_post = f"{discourse_url}/posts/{str(id)}.json"
            res = requests.get(url_to_get_post)
            post = res.json()
            if post.get('user_deleted'):  # ignore deleted posts
                if DEBUG:
                    print(f"post deleted: {post['username']}, {post['cooked']}")
                read_post_ids.append(post['id'])
                continue
            else:
                utterance = post['cooked'].replace("<p>", "").replace("</p>", "")
                read_post_ids.append(post['id'])
                post_info = {"user_name": post['username'], "utterance": utterance}
                result.append(post_info)
    if DEBUG:
        print("new posts: " + str(result))
    return result


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', type=str)
    args = parser.parse_args()

    with open(args.config_file, encoding="utf-8") as fp:
        config: Dict[str, Any] = yaml.safe_load(fp)

    dialogue_processor = DialogueProcessor(args.config_file, {"my_name": discourse_username})

    previous_time = time.time()

    read_post_id_list(topic_id)

    # start conversation
    initial_response: Dict[str, Any] = dialogue_processor.process({"user_id": discourse_username}, initial=True)
    session_id: str = initial_response['session_id']
    system_utterance: str = initial_response['system_utterance']
    if system_utterance:
        print("Posting utterance: " + system_utterance)
        res = post_in_topic(system_utterance, topic_id)
        print("Response is: " + str(res))

    # after starting conversation
    while True:

        current_time = time.time()
        time_to_sleep = previous_time + INTERVAL - current_time
        if time_to_sleep > 1.0:
            if DEBUG:
                print(f"sleeping {str(time_to_sleep)} sec.")
            time.sleep(time_to_sleep)
        previous_time = time.time()

        # check new posts
        new_posts = get_new_posts_in_topic(topic_id)
        if DEBUG:
            print(f"Got {len(new_posts)} new posts.")

        # when there are multiple new posts, posts but last one are sent to DialBB but no response required
        if len(new_posts) > 1:
            for post_info in new_posts[:-1]:  # but last
                if DEBUG:
                    print("new post info (no response required): " + str(post_info))
                if post_info['user_name'] not in participants:
                    participants.append(post_info['user_name'])
                response: Dict[str, Any] \
                    = dialogue_processor.process({"user_id": post_info['user_name'],
                                                  "session_id": session_id,
                                                  "user_utterance": post_info["utterance"],
                                                  "aux_data": {"participants": participants,
                                                               "no_response_required": True}},
                                                 initial=False)

        if new_posts:
            post_info = new_posts[-1]  # last one
            if DEBUG:
                print("new post info (response required): " + str(post_info))
            if post_info['user_name'] not in participants:
                participants.append(post_info['user_name'])
            # no response is required after self's utterance
            no_response_required = (post_info['user_name'] == discourse_username)
            response: Dict[str, Any] \
                = dialogue_processor.process({"user_id": post_info['user_name'],
                                              "session_id": session_id,
                                              "user_utterance": post_info["utterance"],
                                              "aux_data": {"participants": participants,
                                                           "no_response_required": no_response_required}},
                                             initial=False)
            system_utterance: str = response['system_utterance']
            if system_utterance:
                print("Posting utterance: " + system_utterance)
                res = post_in_topic(system_utterance, topic_id)
                print("Response is: " + str(res))





