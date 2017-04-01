import constants
import random

def get_last_element(list):

    if len(list) > 0:
        return list[-1]

def generate_unique(excluded, boundaries=constants.BOUNDARIES):

    ''' Generate unique random number '''
    ''' boundaries is tuple with upper and lower generation boundary, '''
    ''' excluded is iterable with blacklisted outputs '''

    while True:
        num = random.randint(boundaries[0], boundaries[1])
        if num not in excluded:
            return num
