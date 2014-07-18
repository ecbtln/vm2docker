import sys
import docker
import os
from filesystem import BaseImageGenerator
import logging

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(message)s')
    logging.debug('Starting conversion...')
    assert os.geteuid() == 0
    DOCKER_HOST = os.environ.get('DOCKER_HOST', None)
    if DOCKER_HOST is not None and len(DOCKER_HOST.strip()) == 0:
        DOCKER_HOST = None
    client = docker.Client(base_url=DOCKER_HOST)
    path_to_root = os.path.abspath(sys.argv[1])
    image_gen = BaseImageGenerator(path_to_root, client)
    docker_dir = image_gen.generate()
    image_gen.clean_up()

# http://stackoverflow.com/questions/19771113/how-to-recursively-diff-without-transversing-filesystems/19771489?noredirect=1#comment38508861_19771489
# http://stackoverflow.com/questions/9102313/rsync-to-get-a-list-of-only-file-names
# http://stackoverflow.com/questions/20929863/within-lxc-docker-container-what-happens-if-apt-get-upgrade-includes-kernel-up
# http://serverfault.com/questions/141773/what-is-archive-mode-in-rsync