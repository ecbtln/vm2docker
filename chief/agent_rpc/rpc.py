__author__ = 'elubin'
from chief.constants.agent import EXIT_CMD, GET_DEPS_CMD, GET_FS_CMD, GET_INSTALLED_CMD



class RPCCommand(object):
    """
    Each subclass will be responsible for handling the behavior of a given RPC command
    """

    COMMAND = None
    LINE_BREAK = '\r\n'
    N_ARGS = 0  # must be at least this many arguments or an exception will be thrown
    FILE_RESPONSE = False

    def __init__(self, socket, cmd=None):
        self.socket = socket
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

    def handle_response(self, path_or_response):
        """
        An abstract method that, by default, just returns the response as was sent through the socket
        """
        return path_or_response

    def __call__(self, *args, **kwargs):
        """
        For now, keyword arguments are not supported
        """
        assert len(kwargs) == 0
        assert len(args) >= self.N_ARGS
        self.socket.sendall(self.format_cmd(self.COMMAND, *args))

        # block until the socket is ready for reading:

        # each response, by default, is guaranteed to write data in plain text format, so we will typically
        # just read the socket until we encounter a null character
        # the get_fs command does something special where it first prints a special sequence to indicate the
        # header for a file, with the associated file length (in bytes)
        # then we will know to read that many bytes, appending to a file as we go
        # generally, we will not serialize anything to a file except for this special file header

        if self.FILE_RESPONSE:
            out = self.socket.recv_file()
        else:
            out = self.socket.recv()

        return self.handle_response(out)

        # self.socket.recv()
        # view = memoryview(self.buf)
        # tbytes = 0
        # while True:
        #     nbytes = self.socket.recv_into(view, BUFFER_SIZE - tbytes)
        #     tbytes += nbytes
        #     if tbytes != BUFFER_SIZE and view[nbytes - 1] == '\x00':
        #         # if we didn't receive a full buffer and the last byte we received was null then stop to interpret
        #         # the message
        #         break
        #     elif tbytes != BUFFER_SIZE:
        #         # we didn't get a full buffer, keep on receiving until we do or the last byte is NULL
        #         view = view[nbytes:]
        #     else:
        #         # buffer is full
        #         # time to create a new buffer and try again
        #         pass
        #
        #
        #
        # if nbytes != BUFFER_SIZE and
        # if 0 in self.buf:
        #     # check whether we got the null character
        # response = self.socket.recv(BUFFER_SIZE)
        # # TODO: check whether there is more to receive or we are done, then do something with the data such as append to a file and repeat
        #
        # return self.handle_response(response)


class ExitCommand(RPCCommand):
    COMMAND = EXIT_CMD


class GetDependenciesCommand(RPCCommand):
    COMMAND = GET_DEPS_CMD
    N_ARGS = 1


class GetInstalledCommand(RPCCommand):
    COMMAND = GET_INSTALLED_CMD


class GetFileSystemCommand(RPCCommand):
    COMMAND = GET_FS_CMD
    FILE_RESPONSE = True
