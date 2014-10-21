__author__ = 'elubin'

import logging
import socket
from rpc import ExitCommand, RPCCommand
from constants.agent import SEND_FILE_HEADER_FMT, DEFAULT_AGENT_PORT
from utils.utils import inheritors
from utils.ringbuffer import ringbuffer
import re
import tempfile
import os


class CommunicationLayer(object):
    """
    A class that can call any of the prescribed RPC by referencing its command name
    """
    def __init__(self, socket_address, port=DEFAULT_AGENT_PORT):
        try:
            conn = socket.create_connection((socket_address, port))
            self.connection = SocketWrapper(conn)
        except socket.error as e:
            raise ValueError("Could not connect to %s on port %d" % (socket_address, port))

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class SocketWrapper(object):
    """
    Helper subclass that facilitates buffered reading of sockets with a specified byte-delimiter
    """
    BUFFER_SIZE = 4096
    SOCKET_TIMEOUT = 120.0  # seems reasonable timeout to allow for long-running commands

    def __init__(self, connection, delimiter='\x00'):
        self.socket_connection = connection
        self.socket_connection.settimeout(self.SOCKET_TIMEOUT)
        self.delimiter = delimiter
        self.buffer = ringbuffer(self.BUFFER_SIZE)

    def close(self):
        self.socket_connection.close()

    def send(self, msg):
        self.socket_connection.sendall(msg)

    def recv(self):
        """
        Receive a socket response as a string and return the string
        """

        def f(buf, n_bytes):
            return self.socket_connection.recv_into(buf, n_bytes)

        output = bytearray()
        found = False
        while not found:
            # read from the ring buffer first to clear out anything still sitting there
            bytes, found = self.buffer.read_until(self.delimiter)
            output.extend(bytes)
            if not found:
                self.buffer.write_to(f)

        return str(output)

    def recv_file(self):
        """
        Parse the socket response for the string detailing how many bytes are in the file, then write the file
        to disk and return a path to it
        """
        header = self.recv()
        regex_pattern = SEND_FILE_HEADER_FMT % ("([0-9]+)", r'([\w\.]+)')
        m = re.match(regex_pattern, header)
        assert m is not None
        nbytes, filename = m.group(1, 2)
        nbytes = int(nbytes)

        def write_data(buf, n_bytes):
            return self.socket_connection.recv_into(buf, n_bytes)

        bytes_received = 0
        bytes_read_from_buffer = 0
        temp_dir = tempfile.mkdtemp()
        target = os.path.join(temp_dir, filename)
        with open(target, 'wb') as f:
            while bytes_read_from_buffer < nbytes:
                # read from the buffer first to clear out anything that's sitting in there
                data = self.buffer.read(nbytes - bytes_read_from_buffer)
                bytes_read_from_buffer += len(data)
                nbytes_received = self.buffer.write_to(write_data, nbytes - bytes_read_from_buffer)
                # read as many bytes as we can (the read from the ringbuffer will happen on the next loop)
                bytes_received += nbytes_received
                f.write(data)
            # These may not be equal because the previous time we read from the socket into the ring buffer, we likely
            # got extra data that's still sitting there.
            assert bytes_received <= bytes_read_from_buffer

        logging.info('%d bytes saved to %s' % (nbytes, target))
        return target



