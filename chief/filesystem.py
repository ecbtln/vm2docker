__author__ = 'elubin'
import os
import glob
import logging
import subprocess
import tempfile
import tarfile
from packagemanager.packagemanager import MultiRootPackageManager
from dockerfile import DiffBasedDockerBuild, DockerBuild, DockerFile
#from include import RESULTS_LOGGER
from utils.utils import rm_rf, extract_tar
from diff import RSyncDiffTool
from ps import ProcessManager

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
    def __init__(self, vm_socket, dclient, process_packages=True, cache=False, filter_deps=False):
        self.docker_client = dclient
        self.process_packages = process_packages
        self.vm_socket = vm_socket
        self.cache = cache
        self.filter_deps = filter_deps

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        base_image_dir = 'root_fs'
        self.base_image_root = os.path.join(self.temp_dir, base_image_dir, '')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_up()
        return False

    def generate_linux_info(self, vm_root):
        self.linux_info = LinuxInfoParser(vm_root).generate_os_info()
        logging.debug('Detected OS: %s' % self.linux_info.get('PRETTY_NAME', self.linux_info.get('DISTRIB_DESCRIPTION')))


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
        repo_tag = DockerFile.format_image_name(repo, tag)
        self.docker_client.pull(repo)
        candidate_image = [x for x in self.docker_client.images() if repo_tag in x['RepoTags']]
        if len(candidate_image) == 1:
            return self.start_image_and_generate_container_id(repo_tag)
        else:
            return None # TODO: this isn't good, need to manually generate base image with debootstrap

    def start_image_and_generate_container_id(self, repo_tag, command='echo FAKECOMMAND'):
        res = self.docker_client.create_container(repo_tag, command=command)
        container_id = res['Id']
        logging.debug('Container ID: %s' % container_id)
        return container_id

    def export_container_to_tar(self, container_id, tar_name='base_linux.tar'):
        # TODO: compare memory usage of python export, i think it loads entire archive into memory which is not what we want
        # TODO; if the python API isn't good enough, then at least use standard python-based piping instead
        abs_tar_path = os.path.join(self.temp_dir, tar_name)
        logging.debug('Writing base image to %s' % abs_tar_path)
        subprocess.check_output('docker export %s > %s' % (container_id, abs_tar_path), shell=True)

        assert tarfile.is_tarfile(abs_tar_path)
        return abs_tar_path

    def extract_tar(self, tar_path, target_dir, clean_up=True):

        if not os.path.isabs(target_dir):
            target_dir = os.path.join(self.temp_dir, target_dir, '')

        return extract_tar(tar_path, target_dir, clean_up)

    def extract_base_image_tar(self, base_tar_path):
        self.extract_tar(base_tar_path, self.base_image_root)

    def generate(self, vm_tag, run_locally=False, tar_options='-z', diff_tool=RSyncDiffTool):
        # get the filesystem from the socket
        new_vm_root = os.path.join(self.temp_dir, 'vm_root', '') # stupid trailing / hack
        logging.debug('Obtaining filesystem from socket connection')
        tar_path = self.vm_socket.get_filesystem(tar_options)
        assert tarfile.is_tarfile(tar_path)
        self.extract_tar(tar_path, new_vm_root)

        self.generate_linux_info(new_vm_root)

        repo = self.linux_info.get('ID', self.linux_info.get('DISTRIB_ID')).lower()

        tag = self.linux_info.get('VERSION_ID', self.linux_info.get('DISTRIB_RELEASE'))
        tag = self.transform_tag(repo, tag)
        container_id = self.find_base_image(repo, tag)
        assert container_id is not None
        base_tar_path = self.export_container_to_tar(container_id)
        self.extract_base_image_tar(base_tar_path)

        if self.process_packages:
            logging.debug('Generating package manager commands...')

            with MultiRootPackageManager(self.vm_socket, repo, tag, self.docker_client, filter_package_deps=self.filter_deps) as m:
                package_file, cmds = m.prepare_vm()
                repo_files = m.vm.REPO_FILES
                clean_cmd = m.vm.get_clean_cmd()

            if len(cmds) > 0:
                with DockerBuild(repo, tag, self.docker_client) as db:

                    if repo_files is not None and len(repo_files) > 0:
                        db.archive(repo_files, new_vm_root, DockerBuild.REPO_INFO)

                    if package_file is not None:
                        package_list_path = os.path.join(db.dir, DockerBuild.PKG_LIST)
                        with open(package_list_path, 'w') as f:
                            f.write(package_file)

                        db.add_file(DockerBuild.PKG_LIST)

                    db.df.add_build_cmds(cmds)
                    db.df.add_build_cmd(clean_cmd)
                    db.serialize()
                    id = db.build('packages-only')

                if id is None:
                    raise ValueError("One or more of the commands failed to execute successfully")
                # once built, we wanna export it and create a diff
                container_id = self.start_image_and_generate_container_id(id)
                tar_name = 'packages.tar'
                abs_tar_path = self.export_container_to_tar(container_id, tar_name)

                self.base_image_root = self.extract_tar(abs_tar_path, 'packages_container')
                repo = id
                tag = None

        # TODO: trash the kernel
        logging.debug('Generating filesystem diff...')
        with diff_tool(self.base_image_root, new_vm_root) as diff_tool_instance:
            diff_tool_instance.do_diff()

            with DiffBasedDockerBuild(diff_tool_instance, repo, tag, self.docker_client) as build:
                ## detect running processes here
                p_manager = ProcessManager(self.vm_socket)
                active_processes = p_manager.get_processes()
                logging.debug("Found the following %d processes running on host: %s", len(active_processes), active_processes)
                build.set_process(active_processes[0])
                build.serialize()
                logging.debug('Docker build is now located at: %s' % build.dir)
                build.build(vm_tag)
                logging.debug("To run the container execute the following:\n$ docker run -P %s" % vm_tag)
                #if run:

                    #res = self.docker_client.create_container(tag)
                    #logging.debug("Kickstarted Docker image with container ID: %s" % res)

    def clean_up(self):
        # delete the temporary directory
        rm_rf(self.temp_dir)
    #
    # def generate_statistics(self, new_vm_root, base_image_root):
    #     thinned_vm_size = recursive_size(new_vm_root)
    #     base_image_size = recursive_size(base_image_root)
    #     diff_size = recursive_size(self.modified_directory)
    #     logging.getLogger(RESULTS_LOGGER).info('VM size: %sMB, Thin VM size: %sMB, Base image size: %sMB, Diff: %sMB', thinned_vm_size, base_image_size, diff_size)




#TODO: make a verify tool that builds the docker file, exports the image, and then does a diff on the resulting filesystem compared to the original VM