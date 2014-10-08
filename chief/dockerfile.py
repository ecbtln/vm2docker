__author__ = 'elubin'
import tempfile
import os
import logging
import json
import re
import tarfile
import subprocess
import shutil
from include import RESULTS_LOGGER
from utils.utils import rm_rf


class DockerFile(object):
    def __init__(self, repo, tag=None):
        self.repo = repo
        self.tag = tag
        self.docker_cmds = []
        self.run_cmd = None

    def _inheritance_line(self):
        return 'FROM %s' % self.format_image_name(self.repo, self.tag)

    @staticmethod
    def format_image_name(repo, tag=None):
        out = repo
        if tag is not None:
            out += ":%s" % tag
        return out

    def serialize(self):
        cmds = [self._inheritance_line()]
        cmds.extend(self.docker_cmds)
        if self.run_cmd is not None:
            cmds.append('CMD %s' % self.run_cmd)
        return '\n'.join(cmds)

    def add_docker_cmd(self, cmd):
        self.docker_cmds.append(cmd)

    def add_docker_cmds(self, cmds):
        self.docker_cmds.extend(cmds)

    def add_build_cmd(self, cmd):
        self.add_docker_cmd('RUN %s' % cmd)

    def add_build_cmds(self, cmds):
        self.add_docker_cmds(['RUN %s' % cmd for cmd in cmds])


class DockerBuild(object):
    SANDBOX_DIR = '/sbx/'  # TODO: make this dynamic/randomized
    PKG_LIST = 'packages.txt'
    REPO_INFO = 'repos.tar'

    def __init__(self, repo, tag, docker_client):
        self.df = DockerFile(repo, tag)
        self.dir = tempfile.mkdtemp()
        self.docker_client = docker_client
        self.process_info = None

    def add_file(self, path_to_file):
        self.df.add_docker_cmd('ADD %s %s' % (path_to_file, self.SANDBOX_DIR))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        rm_rf(self.dir)
        return False

    @classmethod
    def path_to_sandbox_item(cls, rel_path):
        return os.path.join(cls.SANDBOX_DIR, rel_path)

    def serialize(self):
        self.df.add_build_cmd('rm -rf %s' % self.SANDBOX_DIR)
        if self.process_info is not None:
            cmds = dockerize_process(self.process_info)
            self.df.add_docker_cmds(cmds)
        contents = self.df.serialize()
        logging.debug('Serialized Dockerfile:\n%s' % contents)
        with open(os.path.join(self.dir, 'Dockerfile'), 'w') as dockerfile:
            dockerfile.write(contents)

    def set_process(self, p_info_object):
        self.process_info = p_info_object

    def build(self, tag):
        stream = self.docker_client.build(path=self.dir, tag=tag)
        logging.debug('Building %s with tag %s' % (self.dir, tag))

        last_msg = None
        for i in stream:
            y = json.loads(i)
            if 'stream' in y:
                last_msg = y['stream'].strip()
                logging.debug(last_msg)
            else:
                if 'error' in y:
                    raise RuntimeError("Docker build failed with error: %s" % repr(y))
                else:
                    logging.debug(repr(y))

        # now extract the image ID
        m = re.match("Successfully built ([a-z0-9]{12})", last_msg)
        if m:
            return m.group(1)

    def archive(self, virtual_path_to_tar_files, root, target_name):
        """
        files_to_tar should be absolute paths
        root should be the root of the filesystem upon which files_to_tar is appended
        target_name is a unique file name given to the resulting tar in the docker build folder
        """


        # TODO: RSYNC and do a diff. if there are no changes, we can just skip this part of the dockerfile to maximize layering
        for x in virtual_path_to_tar_files:
            assert os.path.isabs(x)

        rel_to_root = [os.path.relpath(x, '/') for x in virtual_path_to_tar_files]
        real_path = [os.path.join(root, x) for x in rel_to_root ]

        tup = zip(virtual_path_to_tar_files, real_path)

        tar = tarfile.open(os.path.join(self.dir, target_name), 'w')

        for vp, rp in tup:
            tar.add(rp, arcname=vp)

        tar.close()

        self.df.add_docker_cmd('ADD %s /' % target_name)


class DiffBasedDockerBuild(DockerBuild):
    def __init__(self, diff_tool, *args, **kwargs):
        """
        diff_tool is an instance of FileSystemDiffTool class
        """
        self.diff_tool = diff_tool
        self.added_diff_cmds = False
        super(DiffBasedDockerBuild, self).__init__(*args, **kwargs)

    def _diff_cmds(self):
        cmds = []

        for fn, d in self.diff_tool.filesystem_diff_files().items():
            # tar each one up, put it in the docker directory, and then return a command to add it to the image
            target_fn = '%s.tar' % fn
            target_tar = os.path.join(self.dir, target_fn)
            c = 'tar -C %s -c . -f %s' % (d, target_tar)
            logging.debug(c)
            subprocess.check_output(c, shell=True)
            logging.getLogger(RESULTS_LOGGER).info('Size of %s: %.2f %s', target_tar, os.path.getsize(target_tar) / (1024.0 * 1024.0), 'MB')
            cmds.append("ADD %s /" % target_fn)

        for fn, target in self.diff_tool.helper_files().items():
            assert os.path.isfile(target)

            # copy it over to the docker directory
            shutil.copyfile(target, os.path.join(self.dir, fn))
            # append the command to add it to the build
            cmds.append("ADD %s %s" % (fn, self.SANDBOX_DIR))

        # ask the diff tool for any commands to process the files
        # we pass in the root of the sandbox directory, so that the diff tool is responsible for resolving the abs path
        for c in self.diff_tool.post_processing_cmds(self.SANDBOX_DIR):
            cmds.append("RUN %s" % c)

        return cmds

    def serialize(self):
        if not self.added_diff_cmds:
            self.df.add_docker_cmds(self._diff_cmds())
            self.added_diff_cmds = True
        super(DiffBasedDockerBuild, self).serialize()


def dockerize_process(p_info):
    # takes in an instance of a ProcessInfo object, returns a sequence of docker commands to run it
    user = "USER %s" % p_info.uname()
    cwd = "WORKDIR %s" % p_info.cwd()
    cmd = "CMD %s" % p_info.cmdline()
    ports = ["EXPOSE %s" % p for p in p_info.ports]
    environment = p_info.environ()
    environ_cmds = ["ENV %s %s" % (k, v) for k, v in environment.items()]
    o = []
    o.append(user)
    o.extend(environ_cmds)
    o.append(cwd)
    o.append(cmd)
    o.extend(ports)
    return o

