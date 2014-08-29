__author__ = 'elubin'




class DockerFile(object):
    CHANGES = 'changes.tar'
    DELETED = 'deleted.txt'


    def __init__(self, repo, tag):
        self.repo = repo
        self.tag = tag
        self.build_cmds = []


    def _inheritance_line(self):
        return 'FROM %(repo)s:%(tag)s' % {'repo': self.repo, 'tag': self.tag}

    def _apply_diff(self):
        return """ADD %(changes)s /
ADD %(deleted)s /src/
RUN xargs -d '\\n' -a /src/%(deleted)s rm -r
RUN rm -rf /src/%(deleted)s
""" % {'changes': self.CHANGES, 'deleted': self.DELETED}


    def _get_cmds(self):
        return '\n'.join('RUN %s' % cmd for cmd in self.build_cmds)

    def serialize(self, pre_diff=False):
        # by default, the diff should be calculated after the package additions
        fmt = None
        if not pre_diff:
            fmt = "%(from)s\n%(cmds)s\n%(diff)s"
        else:
            fmt = "%(from)s\n%(diff)s\n%(cmds)s"

        return fmt % {'from': self._inheritance_line(), 'cmds': self._get_cmds(), 'diff': self._apply_diff()}


    def add_build_cmd(self, cmd):
        self.build_cmds.append(cmd)

    def add_build_cmds(self, cmds):
        self.build_cmds.extend(cmds)




