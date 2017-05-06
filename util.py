import constants
import os
import base64
import time

def get_revision(list, index):

    if len(list) == 0 or len(list) <= index:
        return []
    else:
        return list[index:]

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
    ''' users is a dicts of a rooms users with timestamp (float, in seconds) at last activity as values '''

    now = time.time()
    for user, timestamp in users.items():
        if (now - timestamp) > constants.EXPIRED_PERIOD:
            del users[user]
