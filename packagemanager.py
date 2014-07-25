__author__ = 'elubin'
import subprocess
import abc
from multiprocessing import Process, Queue
import os
import tempfile
import logging
from utils import generate_regexp

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
            logging.debug(subprocess.check_output(cmd, shell=True))

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
        pass

    # These two abstract methods should be subclassed and return a command to do the following
    @abc.abstractmethod
    def _install_cmds(self, packages, relative=False):
        pass

    @abc.abstractmethod
    def _uninstall_cmds(self, packages, relative=False):
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
    #PACKAGE_BLACKLIST = {'friendly-recovery', 'linux-image-.*'}
    # use dpkg -r to remove packages one at a time
    # use dpkg -i to install them after downloading with apt-get download pkg_name
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
            return ['apt-get install %s' % ' '.join(packages)]


    def _uninstall_cmds(self, packages, relative=False):
        if len(packages) == 0:
            return []
        if relative:
            return ['dpkg --root=%s -r %s' % (self.root, ' '.join(packages))]
        else:
            return ['apt-get remove %s' % ' '.join(packages)]
            #return ['dpkg -r %s' % (' '.join(packages))]


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
        self.vm.uninstall(to_uninstall)

        # step 2. install packages that are on base image but not on VM
        #self.vm.install(to_install)

        # step 3. return commands to undo the effects
        cmds = self.vm._uninstall_cmds(to_install)
        cmds.extend(self.vm._install_cmds(to_uninstall))
        return cmds

    def clean_up(self):
        self.base_image.clean_up()
        self.vm.clean_up()

