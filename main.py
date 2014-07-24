import sys
import docker
import os
from filesystem import BaseImageGenerator
import logging
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='An automated command-line tool to convert virtual machines to layered docker images')
    parser.add_argument('vm_root', help='The path to the root of the virtual machine filesystem')
    parser.add_argument('--tag', default='my-vm', type=str, help='The tag to give the VM in docker')
    parser.add_argument('--packages', dest='packages', action='store_true')
    parser.add_argument('--no-packages', dest='packages', action='store_false')
    parser.set_defaults(packages=False)
    args = parser.parse_args()

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(message)s')
    logging.debug('Starting conversion...')
    assert os.geteuid() == 0
    DOCKER_HOST = os.environ.get('DOCKER_HOST', None)
    if DOCKER_HOST is not None and len(DOCKER_HOST.strip()) == 0:
        DOCKER_HOST = None
    client = docker.Client(base_url=DOCKER_HOST)
    vm_root = os.path.abspath(args.vm_root)
    tag_name = args.tag

    # TODO: use a context manager so things automatically get cleaned up
    image_gen = BaseImageGenerator(vm_root, client, process_packages=args.packages)
    docker_dir = image_gen.generate(tag_name)
    #image_gen.clean_up()



# http://stackoverflow.com/questions/19771113/how-to-recursively-diff-without-transversing-filesystems/19771489?noredirect=1#comment38508861_19771489
# http://stackoverflow.com/questions/9102313/rsync-to-get-a-list-of-only-file-names
# http://stackoverflow.com/questions/20929863/within-lxc-docker-container-what-happens-if-apt-get-upgrade-includes-kernel-up
# http://serverfault.com/questions/141773/what-is-archive-mode-in-rsync