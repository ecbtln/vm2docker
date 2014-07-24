__author__ = 'elubin'
import subprocess
import abc
from multiprocessing import Process, Queue
import os
import tempfile
import logging


class ChrootManager(object):
    def __init__(self, root):
        self.root = root
        self.queue = Queue(1)

    # TODO: convert to the with format, so we could do with change_root(root) as root: do some commands
    def call(self, f, *args, **kwargs):
        def wrapped_f(*args, **kwargs):
            try:
                os.chdir(self.root)
                os.chroot('.')
            except OSError as e:
                self.queue.put(e)
            try:
                output = f(*args, **kwargs)
                self.queue.put(output)
            except Exception as e:
                self.queue.put(e)
        p = Process(target=wrapped_f, args=args, kwargs=kwargs)
        p.start()
        result = self.queue.get()
        if isinstance(result, OSError):
            raise result
        p.join()
        return result


class PackageManager(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, root):
        self.root = root
        self.to_clean = []

    def _exec_in_jail(self, cmds):
        if len(cmds) == 0:
            return
        f = lambda: [subprocess.check_output(cmd, shell=True) for cmd in cmds]
        return ChrootManager(self.root).call(f)

    def get_installed(self):
        return ChrootManager(self.root).call(self._get_installed)

    def install(self, packages):
        return self._exec_in_jail(self._install_cmds(packages))

    def uninstall(self, packages):
        return self._exec_in_jail(self._uninstall_cmds(packages))

    @staticmethod
    def convert_install_to_deinstall(pkg):
        spl = pkg.split()
        spl[1] = 'deinstall'
        return ' '.join(spl)

    @abc.abstractmethod
    def _get_installed(self):
        pass

    # These two abstract methods should be subclassed and return a command to do the following
    @abc.abstractmethod
    def _install_cmds(self, packages):
        pass

    @abc.abstractmethod
    def _uninstall_cmds(self, packages):
        pass

    @staticmethod
    def package_manager(system):
        if system == 'ubuntu':
            return DebianPackageManager

    def clean_up(self):
        for f in self.to_clean:
            os.remove(f)


class DebianPackageManager(PackageManager):
    """
    For debian-like systems aka Ubuntu
    http://kvz.io/blog/2007/08/03/restore-packages-using-dselectupgrade/
    """
    def _get_installed(self):
        return [' '.join(x.split()) for x in subprocess.check_output('dpkg --get-selections | grep -v deinstall', shell=True).splitlines()]

    def _install_cmds(self, packages):
        if len(packages) == 0:
            return []
        return self._add_or_remove(packages)

    def _add_or_remove(self, package_commands):
        fd, filepath = tempfile.mkstemp(suffix='.txt')
        self.to_clean.append(filepath)
        cmd0 = 'echo -e "%s" > %s' % ("\\n".join(package_commands), filepath)
        cmd1 = 'dpkg --set-selections < %s' % filepath
        cmd2 = 'apt-get -y update'
        cmd3 = 'apt-get -y dselect-upgrade'
        return [cmd0, cmd1, cmd2, cmd3]

    def _uninstall_cmds(self, packages):
        if len(packages) == 0:
            return []
        packages = (self.convert_install_to_deinstall(pkg) for pkg in packages)
        return self._add_or_remove(packages)


class MultiRootPackageManager(object):
    def __init__(self, base_image_root, vm_root, os):
        cls = PackageManager.package_manager(os)
        self.base_image = cls(base_image_root)
        self.vm = cls(vm_root)

    def prepare_vm(self):
        base_installed = set(self.base_image.get_installed())
        vm_installed = set(self.vm.get_installed())

        to_install = base_installed - vm_installed
        to_uninstall = vm_installed - base_installed
        logging.debug('%d packages to install on the docker image' % len(to_uninstall))
        logging.debug('%d packages to uninstall on the docker image' % len(to_install))

        # step 1. uninstall packages that are on VM but not on base image
        #self.vm.uninstall(to_uninstall)

        # step 2. install packages that are on base image but not on VM
        #self.vm.install(to_install)

        # step 3. return commands to undo the effects
        cmds = self.vm._uninstall_cmds(to_install)
        cmds.extend(self.vm._install_cmds(to_uninstall))
        return cmds

    def clean_up(self):
        self.base_image.clean_up()
        self.vm.clean_up()

