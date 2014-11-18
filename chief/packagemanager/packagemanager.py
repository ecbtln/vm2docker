__author__ = 'elubin'

import abc
import logging

from utils.utils import generate_regexp, rm_rf
from dependencygraph import filter_non_dependencies
from dockerfile import DockerBuild, DockerFile
import constants.agent


class PackageManager(object):
    __metaclass__ = abc.ABCMeta
    PACKAGE_BLACKLIST = None
    PACKAGE_WHITELIST = None
    REPO_FILES = None

    INSTALL_CMD_FMT = ''
    UNINSTALL_CMD_FMT = ''
    CLEAN_CMD = None
    RELOAD_REPO_CMD = None
    OS_NAME = None


    CACHED_FILES = {}

    def __init__(self, vm_socket=None, image_repo_tag=None, docker_client=None):
        assert vm_socket is not None or image_repo_tag is not None
        self.vm_socket = vm_socket
        self.image_repo_tag = image_repo_tag
        self.docker_client = docker_client

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

    def _get_installed(self):
        if self.vm_socket is not None:
            installed = self.vm_socket.get_installed()
        else:
            assert self.docker_client is not None
            repo, tag = self.image_repo_tag
            parent = DockerFile.format_image_name(repo, tag)
            res = self.docker_client.create_container(parent, command=self._get_installed_cmd())
            container_id = res['Id']
            self.docker_client.start(res)
            assert self.docker_client.wait(res) == 0  # wait until command completes successfull
            installed = self.docker_client.logs(container_id)
        return self._process_get_installed(installed)

    def _process_get_installed(self, res):
        return res

    def _get_installed_cmd(self):
        os = self.OS_NAME
        return getattr(constants.agent, '%s__GET_INSTALLED_CMD' % os)

    @staticmethod
    def package_manager(system):
        if system == 'ubuntu':
            return DebianPackageManager
        elif system == 'centos':
            return YumPackageManager

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
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


    # def delete_cached_files(self):
    #     proper_path = (os.path.join(self.root, os.path.relpath(f, '/')) for f in self.CACHED_FILES)
    #     for f in proper_path:
    #         rm_rf(f)

    def get_dependencies(self, pkg):
        return []


class YumPackageManager(PackageManager):
    REPO_FILES = ['/etc/yum.conf', '/etc/yum.repos.d']
    CLEAN_CMD = 'yum clean all'
    INSTALL_CMD_FMT = 'yum -y install %s'
    UNINSTALL_CMD_FMT = 'yum erase %s'
    OS_NAME = 'CENTOS'
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

    def _process_get_installed(self, res):
        return res.splitlines()

    def get_dependencies(self, pkg):
        output = self.vm_socket.get_dependencies(pkg)
        if output == '':
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
    OS_NAME = 'UBUNTU'

    def _process_get_installed(self, res):
        return [x.split()[0] for x in res.splitlines() if 'deinstall' not in x]

    def get_dependencies(self, pkg):
        output = self.vm_socket.get_dependencies(pkg)
        if output == '':
            return []
        dependencies = [line.split()[1] for line in output.splitlines()]
        return list(set(dependencies))


class ZypperPackageManager(PackageManager):
    # TODO fix these
    INSTALL_CMD_FMT = 'zypper install %s'
    UNINSTALL_CMD_FMT = 'zypper remove %s'

    def _process_get_installed(self, res):
        return res.splitlines()


class MultiRootPackageManager(object):
    def __init__(self, vm_socket, os, tag, docker_client, filter_package_deps=True):
        """
        base_image_identifier is a string likely combining repo:tag such as ubuntu:14.04 so we can execute the command
        that we need to in the given docker container
        """
        cls = PackageManager.package_manager(os)
        logging.debug('Using class %s for OS; %s' % (repr(cls), os))
        self.base_image = cls(image_repo_tag=(os, tag), docker_client=docker_client)
        self.vm = cls(vm_socket=vm_socket)
        self.filter_pkg_deps = filter_package_deps

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.base_image.__exit__(exc_type, exc_val, exc_tb)
        self.vm.__exit__(exc_type, exc_val, exc_tb)
        return False

    def prepare_vm(self):
        vm_installed = set(self.vm.get_installed())
        base_installed = set(self.base_image.get_installed())

        to_remove = base_installed - vm_installed
        to_install = vm_installed - base_installed

        if self.filter_pkg_deps:
            before_dep_filter = len(to_install)
            to_install = filter_non_dependencies(to_install, self.vm.get_dependencies)
            after_dep_filter = len(to_install)
            logging.debug('Filter by dependency cut down %d packages to %d' % (before_dep_filter, after_dep_filter))

        return self.vm.install_uninstall(to_install, to_remove, DockerBuild.path_to_sandbox_item(DockerBuild.PKG_LIST))


