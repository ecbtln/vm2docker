__author__ = 'elubin'
import subprocess
import abc
from multiprocessing import Process, Queue
import os
import logging

from utils import generate_regexp, rm_rf
from chief.packagemanager.dependencygraph import filter_non_dependencies
from chief.dockerfile import DockerBuild


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
    PACKAGE_WHITELIST = None
    REPO_FILES = None

    INSTALL_CMD_FMT = ''
    UNINSTALL_CMD_FMT = ''
    CLEAN_CMD = None
    RELOAD_REPO_CMD = None


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
        # filter out the blacklisted and white listed items
        if self.PACKAGE_WHITELIST is not None:
            regexp = generate_regexp(self.PACKAGE_WHITELIST)
            logging.debug('Only packages that match %s are allowed' % regexp.pattern)
            installed = [x for x in installed if regexp.match(x)]

        if self.PACKAGE_BLACKLIST is not None:
            regexp = generate_regexp(self.PACKAGE_BLACKLIST)
            logging.debug('Ignoring packages that match %s' % regexp.pattern)
            installed = [x for x in installed if not regexp.match(x)]

        return installed

    @abc.abstractmethod
    def _get_installed(self):
        return []

    @staticmethod
    def package_manager(system):
        if system == 'ubuntu':
            return DebianPackageManager
        elif system == 'centos':
            return YumPackageManager

    def clean_up(self):
        for f in self.to_clean:
            os.remove(f)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_up()
        return False

    def get_reload_repo_cmd(self):
        return self.RELOAD_REPO_CMD

    def get_clean_cmd(self):
        return self.CLEAN_CMD

    def get_install_cmd_fmt(self):
        return self.INSTALL_CMD_FMT

    def get_uninstall_cmd_fmt(self):
        return self.UNINSTALL_CMD_FMT

    def install_uninstall(self, to_install, to_uninstall, path_to_list):
        """
        Generate a file that will then be added to the docker image at the given path.

        Return a tuple of the file contents, and then a list of commands to execute to process this file on the host
        """
        cmds = []
        if self.get_reload_repo_cmd() is not None:
            cmds.append(self.get_reload_repo_cmd())

        if len(to_uninstall) > 0:
            cmds.append(self.get_uninstall_cmd_fmt() % ' '.join(to_uninstall))

        if len(to_install) > 0:
            cmds.append(self.get_install_cmd_fmt() % ' '.join(to_install))
        return None, cmds


    def delete_cached_files(self):
        proper_path = (os.path.join(self.root, os.path.relpath(f, '/')) for f in self.CACHED_FILES)
        for f in proper_path:
            rm_rf(f)

    def get_dependencies(self, pkg):
        return []


class YumPackageManager(PackageManager):
    REPO_FILES = ['/etc/yum.conf', '/etc/yum.repos.d']
    CLEAN_CMD = 'yum clean all'
    INSTALL_CMD_FMT = 'yum -y install %s'
    UNINSTALL_CMD_FMT = 'yum erase %s'

    PACKAGE_BLACKLIST = {'systemd.*', 'fakesystemd.*'}

# yum is protected, need to make sure to not remove anything that yum depends on
#     [root@localhost vm2docker]# repoquery --requires --resolve yum
# cpio-0:2.11-22.el7.x86_64
# bash-0:4.2.45-5.el7.x86_64
# diffutils-0:3.3-4.el7.x86_64
# diffutils-0:3.3-4.el7.i686
# python-0:2.7.5-16.el7.x86_64
# python-iniparse-0:0.4-9.el7.noarch
# pygpgme-0:0.3-9.el7.x86_64
# rpm-python-0:4.11.1-16.el7.x86_64
# yum-metadata-parser-0:1.1.4-10.el7.x86_64
# pyliblzma-0:0.5.3-11.el7.x86_64
# rpm-0:4.11.1-16.el7.x86_64
# pyxattr-0:0.5.1-5.el7.x86_64
# python-urlgrabber-0:3.10-4.el7.noarch
# yum-plugin-fastestmirror-0:1.1.31-24.el7.noarch

    def _get_installed(self):
        return subprocess.check_output('rpm -qa --root=%s --queryformat \'%s\'' % (self.root, '%{NAME}\\n'), shell=True).splitlines()


    def get_dependencies(self, pkg):
        try:
            output = subprocess.check_output('repoquery --requires --resolve %s --qf %s' % (pkg, '%{NAME}'), shell=True).splitlines()
        except subprocess.CalledProcessError:
            return []
        return list(set(output))

class DebianPackageManager(PackageManager):
    """
    For debian-like systems aka Ubuntu
    http://kvz.io/blog/2007/08/03/restore-packages-using-dselectupgrade/
    """
    PACKAGE_BLACKLIST = {'linux-.*', 'grub-.*', 'dictionaries-common', 'wbritish', 'console-setup', 'ubuntu-minimal', 'resolvconf', 'kbd'}
    REPO_FILES = ['/etc/apt/']
    #PACKAGE_WHITELIST = {'telnet'}
    # use dpkg -r to remove packages one at a time
    # use dpkg -i to install them after downloading with apt-get download pkg_name


    CLEAN_CMD = 'apt-get clean'
    RELOAD_REPO_CMD = 'apt-get update'
    INSTALL_CMD_FMT = 'apt-get install -y %s'
    UNINSTALL_CMD_FMT = 'apt-get remove --purge -y %s'

    #CACHED_FILES = {'/var/cache/apt/pkgcache.bin', '/var/cache/apt/srcpkgcache.bin'}
    def _get_installed(self):
        return [x.split()[0] for x in subprocess.check_output('dpkg --get-selections --root=%s | grep -v deinstall' % self.root, shell=True).splitlines()]

    def get_dependencies(self, pkg):
        try:
            output = subprocess.check_output('apt-cache depends %s | grep "Depends:"' % pkg, shell=True)
        except subprocess.CalledProcessError:
            return []
        dependencies = [line.split()[1] for line in output.splitlines()]
        return dependencies


class ZypperPackageManager(PackageManager):
    # TODO fix these
    INSTALL_CMD_FMT = 'zypper install %s'
    UNINSTALL_CMD_FMT = 'zypper remove %s'

    def _get_installed(self):
        return subprocess.check_output('rpm -qa --root=%s' % self.root, shell=True).splitlines()


class MultiRootPackageManager(object):
    def __init__(self, base_image_root, vm_root, os, delete_cached_files=True, filter_package_deps=False):
        cls = PackageManager.package_manager(os)
        logging.debug('Using class %s for OS; %s' % (repr(cls), os))
        self.base_image = cls(base_image_root)
        self.vm = cls(vm_root)
        self.delete_cached_files = delete_cached_files
        self.filter_pkg_deps = filter_package_deps

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.base_image.__exit__(exc_type, exc_val, exc_tb)
        self.vm.__exit__(exc_type, exc_val, exc_tb)
        return False

    def prepare_vm(self, read_only=True):
        base_installed = set(self.base_image.get_installed())
        vm_installed = set(self.vm.get_installed())

        to_remove = base_installed - vm_installed
        to_install = vm_installed - base_installed



        if self.filter_pkg_deps:
            before_dep_filter = len(to_install)
            to_install = filter_non_dependencies(to_install, self.vm.get_dependencies)
            after_dep_filter = len(to_install)
            logging.debug('Filter by dependency cut down %d packages to %d' % (before_dep_filter, after_dep_filter))


        # if not read_only:
        #     logging.debug('%d packages to uninstall from the vm clone' % len(to_uninstall))
        #     logging.debug('%d packages to install on the vm clone' % len(to_install))
        #
        #     # step 1. uninstall packages that are on VM but not on base image
        #     self.vm.uninstall(to_uninstall)
        #
        #     # step 2. install packages that are on base image but not on VM
        #     self.vm.install(to_install)
        #
        #     if self.delete_cached_files:
        #         logging.debug('VM size before cache purge %dMB' % recursive_size(self.vm.root))
        #         self.vm.delete_cached_files()
        #         logging.debug('VM size after cache purge %dMB' % recursive_size(self.vm.root))
        #
        # # step 3. return commands to undo the effects
        # cmds = self.vm._uninstall_cmds(to_install)
        # cmds.extend(self.vm._install_cmds(to_uninstall))
        # return cmds

        return self.vm.install_uninstall(to_install, to_remove, DockerBuild.path_to_sandbox_item(DockerBuild.PKG_LIST))


