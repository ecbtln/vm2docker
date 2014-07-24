__author__ = 'elubin'
import os
import glob
import logging
import subprocess
import tempfile
import tarfile
import shutil
import json
from utils import recursive_size
import re
from packagemanager import MultiRootPackageManager


class LinuxInfoParser(object):
    def __init__(self, path_to_root):
        self.path_to_root = path_to_root

    def _parse_os_info(self, file_paths):
        out = {}
        for path in file_paths:
            with open(path, 'r') as f:
                input = f.read()
                for line in input.splitlines():
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if value[0] == '"' and value[-1] == '"':
                            out[key] = value[1:-1]
                        else:
                            out[key] = value
        return out

    def generate_os_info(self):
        etc = os.path.join(self.path_to_root, 'etc', '*-release')
        files = glob.glob(etc)
        return self._parse_os_info(files)


class BaseImageGenerator(object):
    def __init__(self, vm_root, dclient, process_packages=True):
        self.docker_client = dclient
        self.vm_root = os.path.join(os.path.abspath(vm_root), '')  # stupid hack to get the trailing slash
        self.temp_dir = tempfile.mkdtemp()
        self.modified_directory = os.path.join(self.temp_dir, 'modded')
        base_image_dir = 'root_fs'
        self.base_image_root = os.path.join(self.temp_dir, base_image_dir, '')
        self.deleted_list = os.path.join(self.temp_dir, 'deleted.txt')
        os.makedirs(self.modified_directory)
        self.generate_linux_info()
        self.process_packages = process_packages
        logging.debug('Detected OS: %s' % self.linux_info.get('PRETTY_NAME', self.linux_info.get('DISTRIB_DESCRIPTION')))

    def generate_linux_info(self):
        self.linux_info = LinuxInfoParser(self.vm_root).generate_os_info()

    @staticmethod
    def transform_tag(repo, tag):
        if repo == 'centos':
            return repo + tag
        else:
            return tag

    def verify_with_user(self):
        confirm = raw_input('Enter the linux release and version of the VM [%s]: ' % self.linux_info['PRETTY_NAME'])
        return confirm.strip() == ''

    def find_base_image(self, repo, tag):
        repo_tag = '%s:%s' % (repo, tag)
        self.docker_client.pull(repo)
        candidate_image = [x for x in self.docker_client.images() if repo_tag in x['RepoTags']]
        if len(candidate_image) == 1:
            return self.start_image_and_generate_container_id(repo_tag)
        else:
            return None # TODO: this isn't good, need to manually generate base image with debootstrap

    def start_image_and_generate_container_id(self, repo_tag):
        res = self.docker_client.create_container(repo_tag, command='echo FAKECOMMAND')
        container_id = res['Id']
        logging.debug('Container ID: %s' % container_id)
        return container_id

    def export_base_image_tar(self, container_id):
        # TODO: compare memory usage of python export, i think it loads entire archive into memory which is not what we want
        # TODO; if the python API isn't good enough, then at least use standard python-based piping instead
        base_tar = 'base_linux.tar'
        base_tar_path = os.path.join(self.temp_dir, base_tar)
        logging.debug('Writing base image to %s' % base_tar_path)
        subprocess.check_output('docker export %s > %s' % (container_id, base_tar_path), shell=True)

        assert tarfile.is_tarfile(base_tar_path)
        return base_tar_path

    def extract_base_image_tar(self, base_tar_path):
        tf = tarfile.open(base_tar_path, 'r')

        os.makedirs(self.base_image_root)

        logging.debug('Extracting base image to %s' % self.base_image_root)
        tf.extractall(self.base_image_root)

        # remove the tar
        os.remove(base_tar_path)

    def generate_diff(self, base_image_root):
        cmd = 'rsync -axHAX --compare-dest=%s %s %s' % (base_image_root, self.vm_root, self.modified_directory)
        logging.debug(cmd)
        subprocess.check_output(cmd, shell=True)

    def _generate_deletions_and_modified(self):
        deleted_dir = os.path.join(self.temp_dir, 'deleted')
        os.makedirs(deleted_dir)
        cmd = 'rsync -axHAX --compare-dest=%s %s %s' % (self.vm_root, self.base_image_root, deleted_dir)
        logging.debug(cmd)
        subprocess.check_output(cmd, shell=True)
        return self._list_all_files_and_folders(deleted_dir)

    @staticmethod
    def _list_all_files_and_folders(dir):
        system_list = list()
        for dirpath, dirnames, filenames in os.walk(dir):
            if dirpath != dir:
                relative_dir = os.path.relpath(dirpath, dir)
            else:
                relative_dir = ''
            system_list.extend([os.path.join(relative_dir, x) for x in filenames])
            system_list.extend([os.path.join(relative_dir, x) for x in dirnames])
        # now reverse the order, so that files get deleted before their parents
        system_list.reverse()
        return system_list

    def generate_deletions(self):
        deletions_and_modifications = self._generate_deletions_and_modified()
        deletions = list()
        for candidate in deletions_and_modifications:
            to_check = os.path.join(self.modified_directory, candidate)
            if not os.path.lexists(to_check):
                #logging.debug('%s: file does not exist' % to_check)
                deletions.append(candidate)
        logging.debug('%d modifications and deletions, %d deletions' % (len(deletions_and_modifications), len(deletions)))
        return deletions

    def generate(self, vm_tag):

        repo = self.linux_info.get('ID', self.linux_info.get('DISTRIB_ID')).lower()


        tag = self.linux_info.get('VERSION_ID', self.linux_info.get('DISTRIB_RELEASE'))
        tag = self.transform_tag(repo, tag)
        container_id = self.find_base_image(repo, tag)
        assert container_id is not None
        base_tar_path = self.export_base_image_tar(container_id)
        self.extract_base_image_tar(base_tar_path)

        cmds = []
        if self.process_packages:
            logging.debug('Generating package manager commands...')

            # the package manager makes changes to the filesystem, so we are first going to clone the vm, and then
            # modify the vm_root path
            new_vm_root = os.path.join(os.path.join(self.temp_dir, 'vm_root'), '') # stupid trailing / hack
            logging.debug('Cloning VM filesystem to be able to make changes...')
            subprocess.check_output('rsync -axHAX --compare-dest=%s %s %s' % (new_vm_root, self.vm_root, new_vm_root), shell=True)
            self.vm_root = new_vm_root
            m = MultiRootPackageManager(self.base_image_root, self.vm_root, repo)
            cmds.extend(m.prepare_vm())
            m.clean_up()



        logging.debug('Generating filesystem diff...')
        self.generate_diff(self.base_image_root)
        exclude = {'\.dockerinit', 'dev.*'}
        options = '|'.join(exclude)
        regexp = re.compile('^(%s)$' % options)
        with open(self.deleted_list, 'w') as text_file:
            # prepend a '/' to every path, we want these to be absolute paths on the new host
            text_file.write('\n'.join('/' + x for x in self.generate_deletions() if not regexp.match(x)))
        path = self.create_docker_image(repo, tag, cmds=cmds)
        logging.debug('Docker build is now located at: %s' % path)
        self.generate_statistics()
        # now build it
        #self.build_and_push_to_registry(path, vm_tag)
        # now push it to the registry (local for now)

    def create_docker_image(self, from_repo, from_tag, cmds=None):
        temp_dir = tempfile.mkdtemp()

        # now tar up the modifications and into the directory
        changes = 'changes.tar'
        tar_file = os.path.join(temp_dir, 'changes.tar')
        subprocess.check_output('tar -C %s -c . -f %s' % (self.modified_directory, tar_file), shell=True)

        # move the deleted
        deleted = 'deleted.txt'
        os.rename(self.deleted_list, os.path.join(temp_dir, deleted))
        df = """FROM %(repo)s:%(tag)s
ADD %(changes)s /
ADD %(deleted)s /src/
RUN xargs -d '\\n' -a /src/%(deleted)s rm -r
RUN rm -rf /src/%(deleted)s""" % {'repo': from_repo, 'tag': from_tag, 'changes': changes, 'deleted': deleted}
        if cmds is not None and len(cmds) > 0:
            rest = '\n'.join('RUN %s' % cmd for cmd in cmds)
        else:
            rest = ''

        df = "%s\n%s" % (df, rest)

        with open(os.path.join(temp_dir, 'Dockerfile'), 'w') as dockerfile:
            dockerfile.write(df)

        return temp_dir

    def build_and_push_to_registry(self, docker_dir, tag):
        for x in self.docker_client.build(path=docker_dir, tag='VM:%s' % tag):
            y = json.loads(x)
            logging.debug(y['stream'])

    def clean_up(self):
        # delete the temporary directory
        shutil.rmtree(self.temp_dir)

    def generate_statistics(self):
        vm_size = recursive_size(self.vm_root) / (1024*1024)
        base_image_size = recursive_size(self.base_image_root) / (1024*1024)
        diff_size = recursive_size(self.modified_directory) / (1024*1024)
        logging.debug('VM size: %sMB, Base image size: %sMB, Diff: %sMB', vm_size, base_image_size, diff_size)
