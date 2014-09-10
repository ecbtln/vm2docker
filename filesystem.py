__author__ = 'elubin'
import os
import glob
import logging
import subprocess
import tempfile
import tarfile
from utils import recursive_size, generate_regexp
from packagemanager.packagemanager import MultiRootPackageManager
from dockerfile import DiffBasedDockerBuild, DockerBuild
from include import RESULTS_LOGGER, RSYNC_OPTIONS


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
    def __init__(self, vm_root, dclient, process_packages=True, cache=False, filter_deps=False):
        self.docker_client = dclient
        self.vm_root = os.path.join(os.path.abspath(vm_root), '')  # stupid hack to get the trailing slash
        self.process_packages = process_packages
        self.generate_linux_info()
        self.cache = cache
        self.filter_deps = filter_deps

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.modified_directory = os.path.join(self.temp_dir, 'modded')
        base_image_dir = 'root_fs'
        self.base_image_root = os.path.join(self.temp_dir, base_image_dir, '')
        self.deleted_list = os.path.join(self.temp_dir, 'deleted.txt')
        os.makedirs(self.modified_directory)
        logging.debug('Detected OS: %s' % self.linux_info.get('PRETTY_NAME', self.linux_info.get('DISTRIB_DESCRIPTION')))
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_up()
        return False

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

    def export_container_to_tar(self, container_id, tar_name='base_linux.tar'):
        # TODO: compare memory usage of python export, i think it loads entire archive into memory which is not what we want
        # TODO; if the python API isn't good enough, then at least use standard python-based piping instead
        abs_tar_path = os.path.join(self.temp_dir, tar_name)
        logging.debug('Writing base image to %s' % abs_tar_path)
        subprocess.check_output('docker export %s > %s' % (container_id, abs_tar_path), shell=True)

        assert tarfile.is_tarfile(abs_tar_path)
        return abs_tar_path

    def extract_tar(self, tar_path, target_dir, clean_up=True):
        assert os.path.isabs(tar_path)
        if not os.path.isabs(target_dir):
            target_dir = os.path.join(self.temp_dir, target_dir, '')

        tf = tarfile.open(tar_path, 'r')

        os.makedirs(target_dir)

        logging.debug('Extracting tar to %s' % target_dir)
        tf.extractall(target_dir)

        if clean_up:
            # remove the tar
            os.remove(tar_path)

        return target_dir

    def extract_base_image_tar(self, base_tar_path):
        self.extract_tar(base_tar_path, self.base_image_root)

    def generate_diff(self, base_image_root, vm_root):
        cmd = 'rsync %s --compare-dest=%s %s %s' % (RSYNC_OPTIONS, base_image_root, vm_root, self.modified_directory)
        logging.debug(cmd)
        subprocess.check_output(cmd, shell=True)

    def _generate_deletions_and_modified(self, base_image_root, vm_root):
        deleted_dir = os.path.join(self.temp_dir, 'deleted')
        os.makedirs(deleted_dir) # rlptgoDxH
        cmd = 'rsync %s --compare-dest=%s %s %s' % (RSYNC_OPTIONS, vm_root, base_image_root, deleted_dir)
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

    def generate_deletions(self, base_image_root, vm_root):
        deletions_and_modifications = self._generate_deletions_and_modified(base_image_root, vm_root)
        deletions = list()
        for candidate in deletions_and_modifications:
            to_check = os.path.join(self.modified_directory, candidate)
            if not os.path.lexists(to_check):
                #logging.debug('%s: file does not exist' % to_check)
                deletions.append(candidate)
        logging.getLogger(RESULTS_LOGGER).info('Diff between parent and child contains:\n%d modifications and additions, %d deletions' % (len(deletions_and_modifications), len(deletions)))
        return deletions

    def generate(self, vm_tag, run_locally=False):

        repo = self.linux_info.get('ID', self.linux_info.get('DISTRIB_ID')).lower()


        tag = self.linux_info.get('VERSION_ID', self.linux_info.get('DISTRIB_RELEASE'))
        tag = self.transform_tag(repo, tag)
        container_id = self.find_base_image(repo, tag)
        assert container_id is not None
        base_tar_path = self.export_container_to_tar(container_id)
        self.extract_base_image_tar(base_tar_path)

        # # the package manager makes changes to the filesystem, so we are first going to clone the vm, and then
        # # modify the vm_root path
        new_vm_root = os.path.join(self.temp_dir, 'vm_root', '') # stupid trailing / hack
        logging.debug('Cloning VM filesystem to be able to make changes...')
        subprocess.check_output('rsync %s --compare-dest=%s %s %s' % (RSYNC_OPTIONS, new_vm_root, self.vm_root, new_vm_root), shell=True)


        if self.process_packages:
            logging.debug('Generating package manager commands...')

            with MultiRootPackageManager(self.base_image_root, new_vm_root, repo, delete_cached_files=self.cache, filter_package_deps=self.filter_deps) as m:
                package_file, cmds = m.prepare_vm(read_only=True)
                repo_files = m.vm.REPO_FILES
                clean_cmd = m.vm.get_clean_cmd()

            if len(cmds) > 0:
                db = DockerBuild(repo, tag, self.docker_client)

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
        self.generate_diff(self.base_image_root, new_vm_root)
        exclude = {'\.dockerinit', 'dev.*'}
        regexp = generate_regexp(exclude)
        with open(self.deleted_list, 'w') as text_file:
            # prepend a '/' to every path, we want these to be absolute paths on the new host
            text_file.write('\n'.join('/' + x for x in self.generate_deletions(self.base_image_root, new_vm_root) if not regexp.match(x)))
        build = self.create_docker_image(repo, tag)
        logging.debug('Docker build is now located at: %s' % build.dir)
        self.generate_statistics(new_vm_root, self.base_image_root)
        # now build it
        self.build_and_push_to_registry(build, vm_tag, run_locally)
        # now push it to the registry (local for now)

    def create_docker_image(self, from_repo, from_tag):
        build = DiffBasedDockerBuild(from_repo, from_tag, self.docker_client)

        # now tar up the modifications and into the directory
        changes = DiffBasedDockerBuild.CHANGES
        tar_file = os.path.join(build.dir, changes)
        subprocess.check_output('tar -C %s -c . -f %s' % (self.modified_directory, tar_file), shell=True)

        logging.getLogger(RESULTS_LOGGER).info('Size of %s: %.2f %s', tar_file, os.path.getsize(tar_file) / (1024.0 * 1024.0), 'MB')
        # move the deleted
        deleted = DiffBasedDockerBuild.DELETED
        os.rename(self.deleted_list, os.path.join(build.dir, deleted))

        build.serialize()

        return build

    def build_and_push_to_registry(self, d_build, tag, run=False):
        d_build.build(tag)

        logging.debug("To run the container execute the following:\n$ docker run -P %s" % tag)
        #if run:

            #res = self.docker_client.create_container(tag)
            #logging.debug("Kickstarted Docker image with container ID: %s" % res)

    def clean_up(self):
        # delete the temporary directory
        #shutil.rmtree(self.temp_dir)
        pass

    def generate_statistics(self, new_vm_root, base_image_root, units='MB'):
        vm_size = recursive_size(self.vm_root)
        thinned_vm_size = recursive_size(new_vm_root)
        base_image_size = recursive_size(base_image_root)
        diff_size = recursive_size(self.modified_directory)
        logging.getLogger(RESULTS_LOGGER).info('VM size: %sMB, Thin VM size: %sMB, Base image size: %sMB, Diff: %sMB', vm_size, thinned_vm_size, base_image_size, diff_size)


# TODO: make a verify tool that builds the docker file, exports the image, and then does a diff on the resulting filesystem compared to the original VM