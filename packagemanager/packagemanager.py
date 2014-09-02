__author__ = 'elubin'
import subprocess
import abc
from multiprocessing import Process, Queue
import os
import tempfile
import logging
from utils import generate_regexp, recursive_size, rm_rf
from os_helpers import debian
from dependencygraph import filter_non_dependencies

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
    PACKAGE_BLACKLIST = None
    CACHED_FILES = {}

    def __init__(self, root):
        self.root = root
        self.to_clean = []

    # def _exec_in_jail(self, cmds):
    #     if len(cmds) == 0:
    #         return
    #     f = lambda: [subprocess.check_output(cmd, shell=True) for cmd in cmds]
    #     return ChrootManager(self.root).call(f)

    def get_installed(self):
        installed = self._get_installed()
        # filter out the blacklisted items
        if self.PACKAGE_BLACKLIST is not None:
            regexp = generate_regexp(self.PACKAGE_BLACKLIST)
            return [x for x in installed if not regexp.match(x)]
        return installed

    def install(self, packages):
        cmds = self._install_cmds(packages, relative=True)
        for cmd in cmds:
            logging.debug(cmd)
            out = subprocess.check_output(cmd, shell=True)
            logging.info(out)

    def uninstall(self, packages):
        cmds = self._uninstall_cmds(packages, relative=True)
        for cmd in cmds:
            logging.debug(cmd)
            try:
                output = subprocess.check_output(cmd, shell=True)
                logging.debug(output)
            except subprocess.CalledProcessError as e:
                logging.warning(e)

    @abc.abstractmethod
    def _get_installed(self):
        return []

    # These two abstract methods should be subclassed and return a command to do the following
    @abc.abstractmethod
    def _install_cmds(self, packages, relative=False):
        return []

    @abc.abstractmethod
    def _uninstall_cmds(self, packages, relative=False):
        return []

    @staticmethod
    def package_manager(system):
        if system == 'ubuntu':
            return DebianPackageManager

    def clean_up(self):
        for f in self.to_clean:
            os.remove(f)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_up()
        return False

    def delete_cached_files(self):
        proper_path = (os.path.join(self.root, os.path.relpath(f, '/')) for f in self.CACHED_FILES)
        for f in proper_path:
            rm_rf(f)


class DebianPackageManager(PackageManager):
    """
    For debian-like systems aka Ubuntu
    http://kvz.io/blog/2007/08/03/restore-packages-using-dselectupgrade/
    """
    #PACKAGE_BLACKLIST = {'friendly-recovery', 'linux-.*', 'libpam.*'}
    # use dpkg -r to remove packages one at a time
    # use dpkg -i to install them after downloading with apt-get download pkg_name

    CACHED_FILES = {'/var/cache/apt/pkgcache.bin', '/var/cache/apt/srcpkgcache.bin'}
    def _get_installed(self):
        return [x.split()[0] for x in subprocess.check_output('dpkg --get-selections --root=%s | grep -v deinstall' % self.root, shell=True).splitlines()]

    def _install_cmds(self, packages, relative=False):
        if len(packages) == 0:
            return []
        if relative:
            download_dir = os.path.join(tempfile.mkdtemp(), '')
            packages_list = ' '.join(packages)
            return ['cd %s; apt-get download %s' % (download_dir, packages_list),
                    'dpkg --root=%s -i %s*' % (self.root, download_dir)]
        else:
            # now we can filter the packages using a dependency graph!
            logging.debug('Before dependency graph, %d packages should be installed' % len(packages))
            logging.debug(packages)
            packages = filter_non_dependencies(packages, debian.get_dependencies)

            logging.debug('After dependency graph, %d packages should be installed' % len(packages))
            logging.debug(packages)
            return ['apt-get install -y %s' % ' '.join(packages)]

    def _uninstall_cmds(self, packages, relative=False):
        if len(packages) == 0:
            return []
        if relative:
            return ['dpkg --root=%s -r %s' % (self.root, ' '.join(packages))]
        else:
            return ['apt-get remove -y %s' % ' '.join(packages)]
            #return ['dpkg -r %s' % (' '.join(packages))]


class MultiRootPackageManager(object):
    def __init__(self, base_image_root, vm_root, os, delete_cached_files=True):
        cls = PackageManager.package_manager(os)
        self.base_image = cls(base_image_root)
        self.vm = cls(vm_root)
        self.delete_cached_files = delete_cached_files

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.base_image.__exit__(exc_type, exc_val, exc_tb)
        self.vm.__exit__(exc_type, exc_val, exc_tb)
        return False

    def prepare_vm(self, read_only=True):
        base_installed = set(self.base_image.get_installed())
        vm_installed = set(self.vm.get_installed())

        to_install = base_installed - vm_installed
        to_uninstall = vm_installed - base_installed

        if not read_only:
            logging.debug('%d packages to uninstall from the vm clone' % len(to_uninstall))
            logging.debug('%d packages to install on the vm clone' % len(to_install))

            # step 1. uninstall packages that are on VM but not on base image
            self.vm.uninstall(to_uninstall)

            # step 2. install packages that are on base image but not on VM
            self.vm.install(to_install)

            if self.delete_cached_files:
                logging.debug('VM size before cache purge %dMB' % recursive_size(self.vm.root))
                self.vm.delete_cached_files()
                logging.debug('VM size after cache purge %dMB' % recursive_size(self.vm.root))

        # step 3. return commands to undo the effects
        cmds = self.vm._uninstall_cmds(to_install)
        cmds.extend(self.vm._install_cmds(to_uninstall))
        return cmds


