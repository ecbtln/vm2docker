__author__ = 'elubin'

import abc
import logging
import subprocess
import tempfile
import os
from utils.utils import rm_rf, list_all_files_and_folders, generate_regexp
from include import RESULTS_LOGGER


class FilesystemDiffTool(object):
    __metaclass__ = abc.ABCMeta

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.debug:
            rm_rf(self.sbx_dir)
        return False

    def __init__(self, from_root, to_root, sandbox_dir=None, debug=False):
        if sandbox_dir is None:
            sandbox_dir = tempfile.mkdtemp()
        logging.debug("Using %s as sandbox directory for diffs" % sandbox_dir)
        self.sbx_dir = sandbox_dir
        self.from_root = from_root
        self.to_root = to_root
        self.processed = False
        self.debug = debug


    #def generate_deletions(self, from_root, to_root, ):

    def post_processing_cmds(self, path_to_sbx):
        """
        After the diff is applied to the base image, any commands needed to execute to process the helper files.
        """
        return []


    @abc.abstractmethod
    def helper_files(self):
        return dict()

    @abc.abstractmethod
    def filesystem_diff_files(self):
        """
        The list of files used by the diff tool that should be tar'ed up and then added to the root namespace (overwriting existing files)
        """
        return dict()

    @abc.abstractmethod
    def do_diff(self):
        assert not self.processed
        self.processed = True


# TODO: abstract out the notion of the root filesystem so that diffs can be computed from any subdirectory. This will be useful when creating diffs for the repository directory, for example.
class RSyncDiffTool(FilesystemDiffTool):
    RSYNC_OPTIONS = '-axHA' # axHAX doesn't work on CentOS7
    MODIFIED_DIRECTORY_NAME = 'modded'
    DELETED_LIST_NAME = 'deleted.txt'

    def do_diff(self):
        super(RSyncDiffTool, self).do_diff()
        modded_directory = os.path.join(self.sbx_dir, self.MODIFIED_DIRECTORY_NAME)
        os.makedirs(modded_directory)

        # funky behavior with rsync if the trailing slashes aren't provided
        from_root = os.path.join(self.from_root, '')
        to_root = os.path.join(self.to_root, '')

        self._generate_changes(from_root, to_root, modded_directory)
        deletions = self._generate_deletions(from_root, to_root, modded_directory)

        exclude = {'\.dockerinit', 'dev.*', 'sys.*', 'proc.*'}
        regexp = generate_regexp(exclude)
        deleted_list_name = os.path.join(self.sbx_dir, self.DELETED_LIST_NAME)
        with open(deleted_list_name, 'w') as text_file:
            # prepend a '/' to every path, we want these to be absolute paths on the new host
            text_file.write('\n'.join('/' + x for x in deletions if not regexp.match(x)))

    def _generate_changes(self, from_root, to_root, target):
        cmd = 'rsync %s --compare-dest=%s %s %s' % (self.RSYNC_OPTIONS, from_root, to_root, target)
        logging.debug(cmd)
        subprocess.check_output(cmd, shell=True)

    def _generate_deletions_and_modified(self, from_root, to_root):
        deleted_dir = os.path.join(self.sbx_dir, 'deleted')
        os.makedirs(deleted_dir) # rlptgoDxH
        cmd = 'rsync %s --compare-dest=%s %s %s' % (self.RSYNC_OPTIONS, to_root, from_root, deleted_dir)
        logging.debug(cmd)
        subprocess.check_output(cmd, shell=True)
        return list_all_files_and_folders(deleted_dir)

    def _generate_deletions(self, from_root, to_root, modified_dir):
        deletions_and_modifications = self._generate_deletions_and_modified(from_root, to_root)
        deletions = list()
        for candidate in deletions_and_modifications:
            to_check = os.path.join(modified_dir, candidate)
            if not os.path.lexists(to_check):
                #logging.debug('%s: file does not exist' % to_check)
                deletions.append(candidate)
        logging.getLogger(RESULTS_LOGGER).info('Diff between parent and child contains:\n%d modifications and additions, %d deletions' % (len(deletions_and_modifications), len(deletions)))
        return deletions

    def helper_files(self):
        """
        Helper files will be added to a sub-directory and then post-processed accordingly.
        """
        return {self.DELETED_LIST_NAME: os.path.join(self.sbx_dir, self.DELETED_LIST_NAME)}

    def filesystem_diff_files(self):
        """
        The list of files used by the diff tool that should be tar'ed up and then added to the root namespace (overwriting existing files)
        """
        return {self.MODIFIED_DIRECTORY_NAME: os.path.join(self.sbx_dir, self.MODIFIED_DIRECTORY_NAME)}

    def post_processing_cmds(self, path_to_sbx):
        return ["xargs -d '\\n' -a %s rm -r" % os.path.join(path_to_sbx, self.DELETED_LIST_NAME)]
