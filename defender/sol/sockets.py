import json
import errno
import socket


class SocketError(Exception):
    pass


class SocketConnectError(SocketError):
    pass


class SocketDisconnectError(SocketError):
    pass


class JsonSocket(object):
    def __init__(self, path):
        self.path = path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_file = self.socket.makefile()

    def connect(self):
        self.socket.connect(self.path)
        greeting = self.read()
        if greeting is None:
            raise SocketConnectError
        return greeting

    def disconnect(self):
        self.socket.close()
        self.socket_file.close()

    def read(self):
        data = self.socket_file.readline()
        if not data:
            return

        return json.loads(data)

    def write(self, msg):
        try:
            self.socket.sendall(msg.encode())
        except socket.error as error:
            if error[0] == errno.EPIPE:
                return
            raise socket.error(error)
        return self.read()
