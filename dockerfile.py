__author__ = 'elubin'
import tempfile
import os
import logging
import json
import re
import tarfile

class DockerFile(object):

    def __init__(self, repo, tag):
        self.repo = repo
        self.tag = tag
        self.docker_cmds = []

    def _inheritance_line(self):
        return 'FROM %(repo)s:%(tag)s' % {'repo': self.repo, 'tag': self.tag}

    def _get_cmds(self):
        return '\n'.join(self.docker_cmds)

    def serialize(self):
        return "%s\n%s" % (self._inheritance_line(), self._get_cmds())

    def add_docker_cmd(self, cmd):
        self.docker_cmds.append(cmd)

    def add_docker_cmds(self, cmds):
        self.docker_cmds.extend(cmds)

    def add_build_cmd(self, cmd):
        self.add_docker_cmd('RUN %s' % cmd)

    def add_build_cmds(self, cmds):
        self.add_docker_cmds(['RUN %s' % cmd for cmd in cmds])


class DockerBuild(object):
    SANDBOX_DIR = '/sbx/' # TODO: make this dynamic/randomized
    PKG_LIST = 'packages.txt'
    REPO_INFO = 'repos.tar'

    def __init__(self, repo, tag, docker_client):
        self.df = DockerFile(repo, tag)
        self.dir = tempfile.mkdtemp()
        self.docker_client = docker_client

    def add_file(self, path_to_file):
        self.df.add_docker_cmd('ADD %s %s' % (path_to_file, self.SANDBOX_DIR))

    @classmethod
    def path_to_sandbox_item(cls, rel_path):
        return os.path.join(cls.SANDBOX_DIR, rel_path)

    def serialize(self):
        self.df.add_build_cmd('rm -rf %s' % self.SANDBOX_DIR)
        contents = self.df.serialize()
        logging.debug('Serialized Dockerfile:\n%s' % contents)
        with open(os.path.join(self.dir, 'Dockerfile'), 'w') as dockerfile:
            dockerfile.write(contents)

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
    CHANGES = 'changes.tar'
    DELETED = 'deleted.txt'


    def _diff_cmds(self):
        return ["ADD %s /" % self.CHANGES,
                "ADD %s %s" % (self.DELETED, self.SANDBOX_DIR),
                "RUN xargs -d '\\n' -a %s rm -r" % self.path_to_sandbox_item(self.DELETED)]

    def serialize(self):
        self.df.add_docker_cmds(self._diff_cmds())
        super(DiffBasedDockerBuild, self).serialize()


