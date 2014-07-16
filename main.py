import sys
import docker
import tarfile
import os

DOCKER_SOCKET = 'tcp://192.168.59.103:2375' #'unix:///var/run/docker.sock'


# Step 1 - mount VDI on OS

path_to_vdi = sys.argv[1]

cmd = 'VBoxManage clonehd %(path)s %(path)s.img --format %(fmt)s' % {'path': path_to_vdi, 'fmt': 'raw'}



def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w") as tar:
        tar.add(source_dir)

# Step 2 - Determine OS



# Step 3 - Match OS with base image


# Step 4 -
tar_filename = 'archive.tar'
make_tarfile(tar_filename, path_to_vdi)
client = docker.Client(base_url=DOCKER_SOCKET)
client.import_image(tar_filename, tag='server-python')




