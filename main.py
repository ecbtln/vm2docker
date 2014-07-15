import sys
import docker
import VirtualBoxManager

DOCKER_SOCKET = 'unix:///var/run/docker.sock'


# Step 1 - mount VDI on OS

path_to_vdi = sys.argv[0]

cmd = 'VBoxManage clonehd %(path)s %(path)s.img --format %(fmt)s' % {'path': path_to_vdi, 'fmt': 'raw'}




# Step 2 - Determine OS



# Step 3 - Match OS with base image


# Step 4 -




client = docker.Client(base_url=DOCKER_SOCKET)
client.import_image(path_to_vdi)




