__author__ = 'elubin'
from chief.constants.agent import EXIT_CMD, GET_DEPS_CMD, GET_FS_CMD, GET_INSTALLED_CMD

BUFFER_SIZE = 4096


class RPCCommand(object):
    """
    Each subclass will be responsible for handling the behavior of a given RPC command
    """

    COMMAND = None
    LINE_BREAK = '\r\n'

    def __init__(self, socket, cmd=None):
        self.socket = socket
        self.socket.settimeout(10.0)
        if cmd is not None:
            self.COMMAND = cmd

    def format_args(self, cmd, *args):
        """
        By default, just take the args, join them by a space, and then append them to the command with a space
        """
        return '%s %s' % (cmd, ' '.join(args))

    def format_cmd(self, cmd, *args):
        """
        Format the args if needed and then append the carriage return
        """
        full_cmd = cmd
        if len(args) > 0:
            full_cmd = self.format_args(cmd, *args)

        return '%s%s' % (full_cmd, self.LINE_BREAK)

    def handle_response(self, path_to_response):
        """
        An abstract method that, by default, just returns the response as was sent through the socket
        """
        return path_to_response

    def __call__(self, *args, **kwargs):
        """
        For now, keyword arguments are not supported
        """
        assert len(kwargs) == 0
        self.socket.sendall(self.format_cmd(self.COMMAND, *args))

        # wait until the socket is ready for reading:

        response = self.socket.recv(BUFFER_SIZE)
        # TODO: check whether there is more to receive or we are done, then do something with the data such as append to a file and repeat

        return self.handle_response(response)


class ExitCommand(RPCCommand):
    COMMAND = EXIT_CMD


class GetDependenciesCommand(RPCCommand):
    COMMAND = GET_DEPS_CMD


class GetInstalledCommand(RPCCommand):
    COMMAND = GET_INSTALLED_CMD


class GetFileSystemCommand(RPCCommand):
    COMMAND = GET_FS_CMD
