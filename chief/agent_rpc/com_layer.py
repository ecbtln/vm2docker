__author__ = 'elubin'

import socket
from rpc import ExitCommand, RPCCommand
from chief.utils import inheritors


class CommunicationLayer(object):
    """
    A class that can call any of the prescribed RPC by referencing its command name
    """
    def __init__(self, socket_address, port):
        self.connection = socket.create_connection((socket_address, port))
        command_classes = inheritors(RPCCommand)
        # now create a dict keyed by the actual command attributes
        self.commands = {}
        for cls in command_classes:
            self.commands[cls.COMMAND] = cls(self.connection)

    def close(self):
        ExitCommand(self.connection)()
        self.connection.close()

    def __getattribute__(self, item):
        """
        If the method isn't found, look it up in the list of RPCs
        """
        if item in self.commands:
            return self.commands[item]
        else:
            return super(CommunicationLayer, self).__getattribute__(item)