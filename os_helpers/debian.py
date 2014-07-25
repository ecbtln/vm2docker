__author__ = 'elubin'
import subprocess


def get_dependencies(pkg):
    try:
        output = subprocess.check_output('apt-cache depends %s | grep "Depends:"' % pkg, shell=True)
    except subprocess.CalledProcessError:
        return []
    dependencies = [line.split()[1] for line in output.splitlines()]
    return dependencies
