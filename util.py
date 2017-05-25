import constants
import os
import base64
import time

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

def generate_unique(excluded):

    ''' Generate unique random number '''
    ''' excluded is iterable with blacklisted outputs '''

    while True:
        num = base64.b64encode(os.urandom(16))
        if num not in excluded:
            return num

def clear_outdated_users(users):

    ''' Clear all outdated users from a room '''
    ''' A user is defined as outdated if it hasn't sent a message within a certain period '''
    ''' users is a dict of a room's users with timestamp (float, in seconds) at last activity as values '''

    now = time.time()
    for user, timestamp in users.items():
        if (now - timestamp) > constants.EXPIRED_PERIOD:
            del users[user]
