__author__ = 'elubin'
import os
import re
import shutil
import importlib
import tarfile
import logging

def class_for_name(module_name, class_name):
    # load the module, will raise ImportError if module cannot be loaded
    m = importlib.import_module(module_name)
    # get the class, will raise AttributeError if class cannot be found
    c = getattr(m, class_name)
    return c

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


def list_all_files_and_folders(d):
    system_list = list()
    for dirpath, dirnames, filenames in os.walk(d):
        if dirpath != d:
            relative_dir = os.path.relpath(dirpath, d)
        else:
            relative_dir = ''
        system_list.extend([os.path.join(relative_dir, x) for x in filenames])
        system_list.extend([os.path.join(relative_dir, x) for x in dirnames])
    # now reverse the order, so that files get deleted before their parents
    system_list.reverse()
    return system_list

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


def extract_tar(tar_path, target_dir, clean_up=True):
    assert os.path.isabs(tar_path)
    assert os.path.isabs(target_dir)
    assert tarfile.is_tarfile(tar_path)
    tf = tarfile.open(tar_path, 'r')

    if not(os.path.exists(target_dir) and os.path.isdir(target_dir)):
        os.makedirs(target_dir)

    logging.debug('Extracting tar to %s' % target_dir)
    tf.extractall(target_dir)

    if clean_up:
        # remove the tar
        os.remove(tar_path)

    return target_dir
