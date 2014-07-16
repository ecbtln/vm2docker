import sys
import docker
import subprocess
import os

DOCKER_SOCKET = 'tcp://192.168.59.103:2375' #'unix:///var/run/docker.sock'


# Step 1 - mount VDI on OS

path_to_vdi = sys.argv[1]
tag_name = sys.argv[2]

cmd = 'VBoxManage clonehd %(path)s %(path)s.img --format %(fmt)s' % {'path': path_to_vdi, 'fmt': 'raw'}




# Step 2 - Determine OS



# Step 3 - Match OS with base image


# Step 4 -



os.environ['DOCKER_HOST'] = DOCKER_SOCKET


excludes = ['sys', 'proc']

print subprocess.check_output('sudo tar --numeric-owner -C %s -c . | sudo docker import - %s' % (path_to_vdi, tag_name), shell=True)