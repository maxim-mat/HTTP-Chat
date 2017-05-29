## @package HTTP--Chat.util Utility module.
## @file util.py Implementation of @ref HTTP--Chat.util
#

import base64
import constants
import os
import time


## Get room revision since the last one.
# @param room (dict) chat room.
# @param index (int) previous revision index.
# @returns (list) all messages since last revision.
#
def get_revision(room, index):

    list = room['messages']
    baseI = room['base_index']
    messages = []
    if len(list) == 0:
        return []
    if len(list) < index:
        index = index - baseI
    for batch in list[index:]:
        for message in batch:
            messages.append(message)
    return messages


## Generate unique random value.
# @param excluded (iterable) blacklisted outputs.
# @returns (str) generated random value
#
def generate_unique(excluded):

    while True:
        val = base64.b64encode(os.urandom(16))
        if val not in excluded:
            return val


## Clear all inactive users from room.
# @param users (dict) room's users storage.
#
def clear_outdated_users(users):

    now = time.time()
    for user, timestamp in users.items():
        if (now - timestamp) > constants.EXPIRED_PERIOD:
            del users[user]
