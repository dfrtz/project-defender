"""Sockets for communication with local and remote devices."""

import errno
import json
import socket


class SocketError(Exception):
    """Base exception thrown when creating, destroying, or interacting with sockets."""
    pass


class SocketConnectError(SocketError):
    """Error with the connection to a socket."""
    pass


class SocketDisconnectError(SocketError):
    """Error during disconnect attempts on a socket."""
    pass


class JsonSocket(object):
    """Socket for communication locally using JSON.

    Attributes:
        path: A string representing the path to a local object.
        socket: A socket which will communicate locally using a file object.
        socket_file: A file object associated with the socket for communication.
    """

    def __init__(self, path):
        self.path = path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_file = self.socket.makefile()

    def connect(self):
        """Opens the initial connection to the underlying socket.

        Returns:
            A string if a connection was successful.

        Raises:
            SocketConnectError: An error with the connection to the socket.
        """
        self.socket.connect(self.path)
        greeting = self.read()
        if greeting is None:
            raise SocketConnectError
        return greeting

    def disconnect(self):
        """Closes the socket and dependencies."""
        self.socket.close()
        self.socket_file.close()

    def read(self):
        """Reads a message from the socket.

        Returns:
            A dictionary converted from a JSON string.
        """
        data = self.socket_file.readline()
        if not data:
            return
        return json.loads(data)

    def write(self, msg):
        """Writes a JSON formatted message to the socket.

        Args:
            msg: A string representing the message to send.

        Returns:
            A string response from the socket.

        Raises:
            socket.error: An error while sending the message.
        """
        try:
            self.socket.sendall(msg.encode())
        except socket.error as error:
            if error.errno == errno.EPIPE:
                return
            raise socket.error(error)
        return self.read()
