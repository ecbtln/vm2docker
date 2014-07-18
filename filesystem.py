__author__ = 'elubin'
import os
import glob
import logging
import subprocess
import tempfile
import tarfile
import shutil


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
    def __init__(self, path_to_root, dclient):
        self.docker_client = dclient
        self.path_to_root = os.path.join(os.path.abspath(path_to_root), '') # stupid hack to get the trailing slash
        self.temp_dir = tempfile.mkdtemp()
        self.modified_directory = os.path.join(self.temp_dir, 'modded')
        os.makedirs(self.modified_directory)
        self.generate_linux_info()
        logging.debug('Detected OS: %s' % self.linux_info['PRETTY_NAME'])

    def generate_linux_info(self):
        self.linux_info = LinuxInfoParser(self.path_to_root).generate_os_info()

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
        subprocess.check_output('sudo docker export %s > %s' % (container_id, base_tar_path), shell=True)

        assert tarfile.is_tarfile(base_tar_path)
        return base_tar_path

    def extract_base_image_tar(self, base_tar_path):
        tf = tarfile.open(base_tar_path, 'r')

        extraction_dir = 'root_fs'
        extraction_path = os.path.join(self.temp_dir, extraction_dir, '')
        os.makedirs(extraction_path)

        logging.debug('Extracting base image to %s' % extraction_path)
        tf.extractall(extraction_path)

        # remove the tar
        os.remove(base_tar_path)

        return extraction_path

    def generate_diff(self, base_image_root):
        cmd = 'sudo rsync -axHAX --compare-dest=%s %s %s' % (base_image_root, self.path_to_root, self.modified_directory)
        logging.debug(cmd)
        subprocess.check_output(cmd, shell=True)

    def generate(self):
        repo = self.linux_info['ID']
        tag = self.linux_info['VERSION_ID']
        tag = self.transform_tag(repo, tag)
        container_id = self.find_base_image(repo, tag)
        assert container_id is not None
        base_tar_path = self.export_base_image_tar(container_id)
        base_image_root = self.extract_base_image_tar(base_tar_path)
        logging.debug('Generating filesystem diff...')
        self.generate_diff(base_image_root)

    def clean_up(self):
        # delete the temporary directory
        shutil.rmtree(self.temp_dir)