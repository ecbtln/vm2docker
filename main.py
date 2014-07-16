import sys
import docker
import subprocess
import os
import tempfile
import glob
import tarfile
import filecmp

assert os.geteuid() == 0

DOCKER_HOST = os.environ.get('DOCKER_HOST', None)
if DOCKER_HOST is not None and len(DOCKER_HOST.strip()) == 0:
    DOCKER_HOST = None


# Step 1 - mount VDI on OS

path_to_root = sys.argv[1]

cmd = 'VBoxManage clonehd %(path)s %(path)s.img --format %(fmt)s' % {'path': path_to_root, 'fmt': 'raw'}




# Step 2 - Determine OS



# Step 3 - Match OS with base image


# Step 4 -



excludes = ['sys', 'proc']

#print subprocess.check_output('sudo tar --numeric-owner -C %s -c . | sudo docker import - %s' % (path_to_root, tag_name), shell=True)



# get release from /etc/*-release
# file is in the following form:
# DISTRIB_ID=Ubuntu
# DISTRIB_RELEASE=12.10
# DISTRIB_CODENAME=quantal
# DISTRIB_DESCRIPTION="Ubuntu 12.10"
# NAME="Ubuntu"
# VERSION="12.10, Quantal Quetzal"
# ID=ubuntu
# ID_LIKE=debian
# PRETTY_NAME="Ubuntu quantal (12.10)"
# VERSION_ID="12.10"
#
# OR
#
# NAME="CentOS Linux"
# VERSION="7 (Core)"
# ID="centos"
# ID_LIKE="rhel fedora"
# VERSION_ID="7"
# PRETTY_NAME="CentOS Linux 7 (Core)"
# ANSI_COLOR="0;31"
# CPE_NAME="cpe:/o:centos:centos:7"
# HOME_URL="https://www.centos.org/"
# BUG_REPORT_URL="https://bugs.centos.org/"
#
#
# So we want to get the value for the key ID, and make the repository name, and then get the VERSION_ID as the tag name


# Once we do so, prompt the user with PRETTY_NAME to verify we are correct

etc = os.path.join(path_to_root, 'etc', '*-release')
files = glob.glob(etc)

def parse_release_files(file_paths):
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


linux_info = parse_release_files(files)
repo = linux_info['ID']
tag = linux_info['VERSION_ID']
pretty_name = linux_info['PRETTY_NAME']


confirm = raw_input('Enter the linux release and version of the VM [%s]: ' % pretty_name)
assert confirm.strip() == ''

def transform_tag(repo, tag):
    if repo == 'centos':
        return repo + tag
    else:
        return tag
tag = transform_tag(repo, tag)


client = docker.Client(base_url=DOCKER_HOST)
client.pull(repo)

# now try to find appropriate image with given tag
repo_tag = '%s:%s' % (repo, tag)
candidate_image = [x for x in client.images() if repo_tag in x['RepoTags']]

assert len(candidate_image) == 1
# TODO: if it wasn't found, then we need to generate a base image here from the given OS

res = client.create_container(repo_tag, command='echo FAKECOMMAND')
container_id = res['Id']

print 'Container ID: %s' % container_id



# TODO: compare memory usage of python export, i think it loads entire archive into memory which is not what we want
# TODO; if the python API isn't good enough, then at least use standard python-based piping instead
temp_dir = tempfile.mkdtemp()
base_tar = 'base_linux.tar'
base_tar_path = os.path.join(temp_dir, base_tar)
print 'Writing base image to %s' % base_tar_path
subprocess.check_output('sudo docker export %s > %s' % (container_id, base_tar_path), shell=True)

assert tarfile.is_tarfile(base_tar_path)


tf = tarfile.open(base_tar_path, 'r')

extraction_dir = 'root_fs'
extraction_path = os.path.join(temp_dir, extraction_dir)
os.makedirs(extraction_path)

print 'Extracting base image to %s' % extraction_path
tf.extractall(extraction_path)


# remove the tar
os.remove(base_tar_path)

sys.stdout = sys.stderr
filecmp.dircmp(path_to_root, extraction_path).report_full_closure()