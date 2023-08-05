"""Sockets for communication with local and remote devices."""

import errno
import json
import socket
from typing import Union


class SocketError(Exception):
    """Base exception thrown when creating, destroying, or interacting with sockets."""


class SocketConnectError(SocketError):
    """Error with the connection to a socket."""


class SocketDisconnectError(SocketError):
    """Error during disconnect attempts on a socket."""


class JsonSocket(object):
    """Socket for communication locally using JSON.

    Attributes:
        path: A string representing the path to a local object.
        socket: A socket which will communicate locally using a file object.
        socket_file: A file object associated with the socket for communication.
    """

    def __init__(self, path: str) -> None:
        """Setup socket for communication."""
        self.path = path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_file = self.socket.makefile()

    def connect(self) -> Union[dict, list]:
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

    def disconnect(self) -> None:
        """Closes the socket and dependencies."""
        self.socket.close()
        self.socket_file.close()

    def read(self) -> Union[dict, list, None]:
        """Reads a message from the socket.

        Returns:
            An object converted from a JSON string.
        """
        result = None
        data = self.socket_file.readline()
        if data:
            result = json.loads(data)
        return result

    def write(self, msg: str) -> Union[dict, list, None]:
        """Writes a JSON formatted message to the socket.

        Args:
            msg: The message to send.

        Returns:
            A response from the socket.

        Raises:
            socket.error: An error while sending the message.
        """
        try:
            self.socket.sendall(msg.encode())
        except socket.error as error:
            if error.errno != errno.EPIPE:
                raise socket.error(error)
        response = self.read()
        return response
