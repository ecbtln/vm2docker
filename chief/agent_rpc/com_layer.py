__author__ = 'elubin'

import socket
from rpc import ExitCommand, RPCCommand
from chief.utils import inheritors, ringbytearray


class CommunicationLayer(object):
    """
    A class that can call any of the prescribed RPC by referencing its command name
    """
    def __init__(self, socket_address, port):
        self.connection = SocketWrapper(socket.create_connection((socket_address, port)))
        command_classes = inheritors(RPCCommand)
        # now create a dict keyed by the actual command attributes
        self.commands = {}
        for cls in command_classes:
            self.commands[cls.COMMAND] = cls(self.connection)

    def close(self):
        ExitCommand(self.connection)()
        self.connection.close()

    def __getattr__(self, item):
        """
        If the method isn't found, look it up in the list of RPCs
        """
        if item in self.commands:
            return self.commands[item]
        else:
            raise AttributeError()


class SocketWrapper(object):
    """
    Helper subclass that facilitates buffered reading of sockets with a specified byte-delimiter
    """
    BUFFER_SIZE = 4096
    SOCKET_TIMEOUT = 5.0

    def __init__(self, connection, delimiter='\x00'):
        self.socket_connection = connection
        self.socket_connection.settimeout(self.SOCKET_TIMEOUT)
        self.delimiter = delimiter
        self.buffer = ringbytearray(self.BUFFER_SIZE)

    def close(self):
        self.socket_connection.close()

    def recv(self):
        """
        Receive a socket response as a string and return the string
        """





        # start with a memory view that uses what's left of the buffer
        view = memoryview(self.buffer)[self.nbytes:]
        output = bytearray()
        while True:
            nbytes = self.socket_connection.recv_into(view, len(view))
            just_written = view[:nbytes]

            idx_of_null = len(self.buffer)
            for i, x in enumerate(just_written):
                if x == self.delimiter:
                    idx_of_null = i + self.nbytes


            self.nbytes += nbytes

            if self.nbytes == len(self.buffer):
                to_append = memoryview(self.buffer)[:idx_of_null] # not including the null character
                output.extend(to_append)  # copy the buffer into the output


                self.nbytes = len(self.buffer) - idx_of_null # reset the nbytes pointer

                if idx_of_null != len(self.buffer):
                    self.buffer[:len(self.buffer) - idx_of_null - 1] = self.buffer[idx_of_null + 1:]
                    return output
                else:
                    view = memoryview(self.buffer)
            else:
                # the buffer isn't full
                # instead we still need to scan for null and only if we find it do we do anything
                if idx_of_null == len(self.buffer):
                    view = view[nbytes:]
                    self.nbytes += nbytes
                else:
                    to_append = memoryview(self.buffer)[:idx_of_null]
                    output.extend(to_append)

                    self.buffer[:len(self.buffer) - idx_of_null - 1] = self.buffer[idx_of_null + 1:]
                    self.nbytes = len(self.buffer) - idx_of_null
                    return output





    def recv_file(self):
        """
        Parse the socket response for the string detailing how many bytes are in the file, then write the file
        to disk and return a path to it
        """
        pass


