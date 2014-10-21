__author__ = 'elubin'
from collections import defaultdict
import logging


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
        return self.vm_socket.get_active_processes(" ".join(pids))

    def find_bound_ports(self, pids_it):
        """
        Return a mapping of pids to a set of bound ports. PIDs are all strings, not integers
        """
        pids = set(pids_it)
        m = defaultdict(lambda: set())
        ns = self.vm_socket.get_bound_sockets().splitlines()[2:]
        for l in ns:
            elts = l.split()
            prt = elts[3].split(':')[1]
            pid = elts[-1].split('/')[0]
            if pid in pids:
                m[pid].add(prt)
        return m

    def get_processes(self):
        pids = self.get_pids()
        proc_info = self.get_pid_info(pids)
        ports = self.find_bound_ports(pids)

        processes = [ProcessInfo(proc_info, ports.get(pid, set())) for pid in pids]

        return processes


class ProcessInfo(object):
    def __init__(self, to_parse, ports):
        self.ports = ports
        input = to_parse.splitlines()
        logging.debug(repr(input))
        self.pid, self.cwd, self.exe, self.uid, self.user, self.cmdline = input[:6]
        env = input[6:]
        self.env = {}
        for l in env:
            if len(l) > 0 and '=' in l:
                key, value = l.split('=', 1)
                self.env[key] = value