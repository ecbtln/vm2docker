__author__ = 'elubin'
import os
import pwd
from utils.utils import extract_tar, rm_rf
import tempfile


class ProcessManager(object):
    def __init__(self, vm_socket):
        self.vm_socket = vm_socket

    def get_pids(self):
        agent_pid = self.vm_socket.get_pid()
        ps_output = self.vm_socket.get_ps()
        # now filter out ps
        return self._filter_ps(ps_output, exclude=agent_pid)

    def _filter_ps(self, input, exclude=None):
        lines = input.splitlines()[1:]
        o = []
        for x in lines:
            spl = x.split()
            if spl[0] != exclude:
                o.append(spl[0])
        return o

    def get_pid_info(self, pids):
        path_to_tar = self.vm_socket.get_active_processes(" ".join(pids))
        return extract_tar(path_to_tar, tempfile.mkdtemp(), clean_up=True)

    # TODO: still needs to be implemented
    def find_bound_ports(self, pids):
        """
        Return a mapping of pids to a set of bound ports. PIDs are all strings, not integers
        """
        ns = self.vm_socket.get_bound_sockets()

        return dict()

    def get_processes(self):
        pids = self.get_pids()
        proc_dir = self.get_pid_info(pids)
        ports = self.find_bound_ports(pids)

        processes = []
        for pid in pids:
            proc_path = os.path.join(proc_dir, pid)
            assert os.path.isdir(proc_path)
            processes.append(ProcessInfo(proc_path, ports.get(pid, set())))

        return processes


# TODO: seems to break when a copy takes place. verify that it works
class ProcessInfo(object):
    """
    A helper class to handle parsing info from the pseudo filesystem in /proc, for a particular process
    """

    def __init__(self, path, ports=None):
        assert os.path.isdir(path), os.path.isabs(path)
        self.path = path
        self.pid = os.path.basename(path)
        if ports is None:
            ports = set()
        self.ports = ports

    def cwd(self):
        return os.readlink(os.path.join(self.path, 'cwd'))

    def exe(self):
        return os.readlink(os.path.join(self.path, 'exe'))

    def _readfile(self, relative_path):
        abs_path = os.path.join(self.path, relative_path)
        with open(abs_path, 'r') as f:
            return f.read()

    def environ(self):
        return self._readfile('environ')

    def cmdline(self):
        return self._readfile('cmdline')

    def uid(self):
        return os.stat(self.path).st_uid

    def uname(self):
        return pwd.getpwuid(self.uid()).pw_name