__author__ = 'elubin'
import subprocess
import abc
from multiprocessing import Process, Queue
import os


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
    #__metaclass__ = abc.ABCMeta

    def __init__(self, root):
        self.root = root

    def _exec_in_jail(self, cmd):
        f = lambda: subprocess.check_output(cmd, shell=True)
        return ChrootManager(self.root).call(f)

    def get_installed(self):
        return ChrootManager(self.root).call(self._get_installed)

    def install(self, packages):
        return self._exec_in_jail(self._install_cmd(packages))

    def uninstall(self, packages):
        return self._exec_in_jail(self._uninstall_cmd(packages))

    @abc.abstractmethod
    def _get_installed(self):
        pass

    # These two abstract methods should be subclassed and return a command to do the following
    @abc.abstractmethod
    def _install_cmd(self, packages):
        pass

    @abc.abstractmethod
    def _uninstall_cmd(self, packages):
        pass

    @staticmethod
    def package_manager(system):
        if system == 'ubuntu':
            return DebianPackageManager


class DebianPackageManager(PackageManager):
    """
    For debian-like systems aka Ubuntu
    http://kvz.io/blog/2007/08/03/restore-packages-using-dselectupgrade/
    """


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


        # step 1. uninstall packages that are on VM but not on base image
        self.vm.uninstall(to_uninstall)

        # step 2. install packages that are on base image but not on VM
        self.vm.install(to_install)

        # step 3. return commands to undo the effects
        return (self.vm._uninstall_cmd(to_install), self.vm._install_cmd(to_uninstall))

