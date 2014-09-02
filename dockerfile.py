__author__ = 'elubin'
import tempfile
import os
import logging
import json


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
        self.add_build_cmd('RUN %s' % cmd)

    def add_build_cmds(self, cmds):
        self.add_build_cmds(['RUN %s' % cmd for cmd in cmds])


class DockerBuild(object):
    def __init__(self, repo, tag, docker_client):
        self.df = DockerFile(repo, tag)
        self.dir = tempfile.mkdtemp()
        self.docker_client = docker_client

    def serialize(self):
        with open(os.path.join(self.dir, 'Dockerfile'), 'w') as dockerfile:
            dockerfile.write(self.df.serialize())

    def build(self, tag):
        stream = self.docker_client.build(path=self.dir, tag=tag)
        logging.debug('Building %s with tag %s' % (self.dir, tag))
        for i in stream:
            y = json.loads(i)
            logging.debug(y['stream'][:-1])


class DiffBasedDockerBuild(DockerBuild):
    CHANGES = 'changes.tar'
    DELETED = 'deleted.txt'

    def _diff_cmds(self):
        return ["ADD %s " % self.CHANGES,
                "ADD %s /src/" % self.DELETED,
                "RUN xargs -d '\\n' -a /src/%s rm -r" % self.DELETED,
                "RUN rm -rf /src/%s" % self.DELETED]

    def serialize(self):
        self.df.add_docker_cmds(self._diff_cmds())
        super(DiffBasedDockerBuild, self).serialize()


