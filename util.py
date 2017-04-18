import constants
import os
import base64

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
