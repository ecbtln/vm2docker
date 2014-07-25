__author__ = 'elubin'
import os
import re

def recursive_size(path):
    sizeof = os.path.getsize
    if os.path.isdir(path):
        # walk it
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                if not os.path.islink(full_path):
                    total_size += sizeof(full_path)
        return total_size
    else:
        return sizeof(path)


def generate_regexp(iterable):
    options = '|'.join(iterable)
    return re.compile('^(%s)$' % options)