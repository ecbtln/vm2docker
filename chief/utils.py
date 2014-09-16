__author__ = 'elubin'
import os
import re
import shutil

def recursive_size(path, divisor=1024*1024):
    sizeof = os.path.getsize
    if os.path.isdir(path):
        # walk it
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                if not os.path.islink(full_path):
                    total_size += sizeof(full_path)
        return total_size / divisor
    else:
        return sizeof(path) / divisor


def generate_regexp(iterable):
    options = '|'.join(iterable)
    return re.compile('^(%s)$' % options)


def rm_rf(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def inheritors(klass):
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses