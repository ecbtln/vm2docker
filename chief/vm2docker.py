#!/usr/bin/python2.7

import sys
import os
import logging
from logging import FileHandler
import argparse
import tempfile
import time
import docker
from filesystem import BaseImageGenerator
from include import RESULTS_LOGGER
from constants.agent import DEFAULT_AGENT_PORT
from agent_rpc.com_layer import CommunicationLayer

if __name__ == '__main__':
    # TODO: add argument for filesystem tar compresssion

    parser = argparse.ArgumentParser(description='An automated command-line tool to convert virtual machines to layered docker images')
    parser.add_argument('vm_ip_address', help='The IP address of the virtual machine')

    parser.add_argument('agent_port', nargs='?', default=os.getenv("AGENT_PORT", DEFAULT_AGENT_PORT), type=int, help='The port on which the agent is running')
    parser.add_argument('--tag', default='my-vm', type=str, help='The tag to give the VM in docker')

    process_pkg_group = parser.add_mutually_exclusive_group()
    process_pkg_group.add_argument('--packages', dest='packages', action='store_true')
    process_pkg_group.add_argument('--no-packages', dest='packages', action='store_false')
    parser.set_defaults(packages=True)

    filter_deps_group = parser.add_mutually_exclusive_group()
    filter_deps_group.add_argument('--filter-deps', dest='filter_deps', action='store_true')
    filter_deps_group.add_argument('--no-filter-deps', dest='filter_deps', action='store_false')
    parser.set_defaults(filter_deps=True)

    clean_cache_group = parser.add_mutually_exclusive_group()
    clean_cache_group.add_argument('--clean-cache', dest='cache', action='store_true')
    clean_cache_group.add_argument('--no-clean-cache', dest='cache', action='store_false')
    parser.set_defaults(cache=False)

    clean_cache_group = parser.add_mutually_exclusive_group()
    clean_cache_group.add_argument('--run', dest='run', action='store_true')
    clean_cache_group.add_argument('--no-run', dest='run', action='store_false')
    parser.set_defaults(run=True)

    args = parser.parse_args()

    # configure the root logger to print all debug messages and above
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(message)s')

    results_logger = logging.getLogger(RESULTS_LOGGER)

    # create a temporary file for the log results
    _handle, path = tempfile.mkstemp(suffix='.txt', prefix='vm2docker__%d' % int(time.time()))

    handler = FileHandler(path)
    handler.setLevel(logging.INFO)
    results_logger.addHandler(handler)

    logging.debug('Starting conversion...')

    # TODO: don't think we need root anymore, but we may for permissions or something
    assert os.geteuid() == 0
    DOCKER_HOST = os.environ.get('DOCKER_HOST', None)
    if DOCKER_HOST is not None and len(DOCKER_HOST.strip()) == 0:
        DOCKER_HOST = None

    client = docker.Client(base_url=DOCKER_HOST)
    vm_socket = CommunicationLayer(args.vm_ip_address, args.agent_port)

    tag_name = args.tag

    with BaseImageGenerator(vm_socket, client, process_packages=args.packages, cache=args.cache, filter_deps=args.filter_deps) as image_gen:
        image_gen.generate(tag_name, run_locally=args.run)

    logging.debug('Results written to %s' % path)



# http://stackoverflow.com/questions/19771113/how-to-recursively-diff-without-transversing-filesystems/19771489?noredirect=1#comment38508861_19771489
# http://stackoverflow.com/questions/9102313/rsync-to-get-a-list-of-only-file-names
# http://stackoverflow.com/questions/20929863/within-lxc-docker-container-what-happens-if-apt-get-upgrade-includes-kernel-up
# http://serverfault.com/questions/141773/what-is-archive-mode-in-rsync