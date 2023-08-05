"""Service requests to and from users with Hypertext Transport Protocol."""

import abc
import base64
import json
import logging
import logging.handlers
import os
import pathlib
import re
import socket
import ssl
import threading

from typing import Any
from typing import Iterable
from typing import Tuple

from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingTCPServer


class ApiService(object):
    """Base API service to control startup, shutdown, and logging of HTTP sockets.

    Attributes:
        config: An ApiConfig to load startup and shutdown information.
        server: A TCPServer instance which will process all HTTP requests.
        logger: A logger instance where all messages will be stored.
    """

    def __init__(self, config: Any) -> None:
        """Initializes the service with a basic configuration and logger."""
        self.config = config
        self.server = None
        self.logger = self.setup_logger()

    def log_message(self, message: str, external: bool = False, level: int = logging.INFO) -> None:
        """Writes a message to the logs and standard output where applicable.

        Args:
            message: Text to write to the logger and user.
            external: Whether the message should be sent to standard (external) output.
            level: Logging level used to control the type of message recorded.
        """
        self.logger.log(level, message)
        if external:
            print(message)

    def set_debug(self, enable: bool = False) -> None:
        """Enables or disables debug output from the server.

        This method is disruptive while the setting is being applied.

        Args:
            enable: Whether debug mode should be enabled.
        """
        self.shutdown()
        if enable:
            self.config.debug = True
            self.log_message('HTTP service enabling debugging', True)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.config.debug = False
            self.log_message('HTTP service disabling debugging', True)
            self.logger.setLevel(logging.INFO)
        self.start()

    def setup_logger(self) -> logging.Logger:
        """Creates a logger to record the lifecycle of the server.

        Returns:
            A logger instance with custom formatting for the server.
        """
        logger = logging.getLogger(__name__)
        if not len(logger.handlers):
            formatter = logging.Formatter(
                fmt='{asctime} - {levelname} - {message}',
                datefmt='%Y-%m-%dT%H:%M:%S.%s',
                style='{'
            )
            file_handler = logging.handlers.RotatingFileHandler(
                self.config.log,
                maxBytes=10000000,
                backupCount=5,
                encoding='UTF-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
        return logger

    def shutdown(self) -> None:
        """Stops the TCPServer and prevents serving new HTTP requests."""
        if self.server is not None:
            self.log_message('HTTP service shutting down', True)
            self.server.socket.close()
            self.server.shutdown()
            self.server = None
            self.log_message('HTTP service offline', True)
        else:
            self.log_message('HTTP service offline. Aborting repeat shutdown.', True)

    def start(self) -> None:
        """Creates the TCPServer thread to service new HTTP requests."""
        if self.server is None:
            self.log_message('HTTP service starting', True)
            self.server = self.config.thread_handler(self.config, False)

            # Manually bind and activate to set socket reuse w/o overriding class
            self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.server_bind()
            self.server.server_activate()

            # Wrap HTTPD socket in SSL if a certificate was provided
            cert_loaded = False
            if self.config.secure:
                if pathlib.Path(self.config.secure).absolute().is_file():
                    # TODO: Validate certificate
                    self.log_message(f'HTTP service loading SSL cert: {self.config.secure}', True)
                    self.server.socket = ssl.wrap_socket(
                        self.server.socket,
                        keyfile=self.config.key,
                        certfile=self.config.secure,
                        server_side=True,
                        ssl_version=ssl.PROTOCOL_TLSv1_2
                    )
                    cert_loaded = True
            # Start HTTPD in new thread to prevent blocking user input
            threading.Thread(target=self.server.serve_forever).start()

            protocol = 'https' if cert_loaded else 'http'
            self.log_message(f'HTTP service listening on {protocol}://{self.config.host}:{self.config.port}', True)
        else:
            self.log_message('HTTP service cannot start, already listening', True)


class ApiHandler(BaseHTTPRequestHandler):
    """Base API request handler to authenticate users and service REST calls over HTTP.

    Attributes:
        api_options: Supported types of HTTP options such as GET, PUT, etc.
        api_versions: Supported API versions uch as 1.0, 1.1, etc.
        api_headers: Valid HTTP headers.
        api_realm: The realm for basic authentication requests.
        file_exts: Valid file extensions that can be requested.
    """

    def __init__(self, *args: Any) -> None:
        """Setup the custom values for this instance before starting to service requests."""
        self.api_options = ['GET']
        self.api_versions = ['1.0']
        self.api_headers = ['Content-Type', 'Content-Length']
        self.api_realm = 'secret'
        self.file_exts = ('.css', '.html', '.js', '.ttf', '.map')

        # Call child API response setup
        self.setup_api()

        # Init must be last, or response will be handled without user configuration
        super(ApiHandler, self).__init__(*args)

    def authenticate(self) -> bool:
        """Authenticates the request's credentials and sends a request for authentication if none are found.

        Returns:
            True if credentials are valid, False if credentials are invalid or not found.
        """
        if not hasattr(self.server, 'authenticate'):
            self.log_message('%s', 'Using auth handler without auth server, skipping authorization')
            return True

        header = self.headers.get('Authorization', None)
        if header is None:
            self.do_AUTHHEAD()
            return False

        # Split header into [Basic] and [username:password] to verify if authentication information was provided.
        headers = header.split()
        if len(headers) < 2 or headers[0] != 'Basic':
            self.do_AUTHHEAD()
            return False

        credentials = base64.b64decode(headers[1].encode()).decode().split(':')
        user = credentials[0]
        password = credentials[1]

        authenticated = self.server.authenticate(user, password)
        if not authenticated:
            self.do_AUTHHEAD()
        return authenticated

    def do_AUTHHEAD(self) -> None:
        """Triggers a basic authentication request from the client using the configured realm."""
        self.send_response(401, self.responses[401][1])
        self.send_header('WWW-Authenticate', f'Basic realm="{self.api_realm}"')
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Authentication Failed')

    def do_GET(self) -> None:
        """Authenticates a user and serves requests for local files, or forwards API calls."""
        if self.path.startswith('/api'):
            args = re.sub('/api(/)?', '', self.path).rstrip('/').split('/')

            if len(args) < 2 or args[0] == '':
                # Bypass authentication if only checking versions
                self.write_response(
                    200,
                    [('Access-Control-Allow-Origin', '*'), ('Content-Type', 'application/json')],
                    f'{{"versions": {json.dumps(self.api_versions)}}}'
                )
                return

            if self.authenticate():
                self.serve_api()
        else:
            if self.authenticate():
                file_path = self.path

                if file_path == '/':
                    file_path = f'{self.server.config.web_root}/index.html'
                else:
                    file_path = self.server.config.web_root + file_path

                if os.path.abspath(file_path).startswith(self.server.config.web_root):
                    # Only serve files under application root or user specified location
                    self.serve_file(file_path)
                else:
                    self.send_error(404, self.responses[404][1])

    def do_OPTIONS(self) -> None:
        """Returns a response to the client containing all valid API methods and headers."""
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', ','.join(self.api_options))
        self.send_header('Access-Control-Allow-Headers', ','.join(self.api_headers))
        self.end_headers()

    def do_POST(self) -> None:
        """Authenticates a user and forwards API POST requests if user session is valid."""
        if self.authenticate():
            if self.path.startswith('/api'):
                self.serve_api()
            else:
                self.send_error(400, self.responses[400][1])

    def do_PUT(self) -> None:
        """Authenticates a user and forwards API PUT requests if user session is valid."""
        if self.authenticate():
            if self.path.startswith('/api'):
                self.serve_api()
            else:
                self.send_error(400, self.responses[400][1])

    def log_message(self, template: str, *args: Any) -> None:
        """Overrides parent logging function from base HTTP request handler to prevent standard out flooding."""
        # Currently no logging of individual requests is performed, just absorb the output.

    def serve_api(self) -> None:
        """Services the root request for all API access by calling child functions based on the path and command type.

        This method will send a list of valid API versions if one is not specified.

        Examples of API translation:
            PUT - http://localhost/api/v1/newhost = put_NEWHOST(args, rdata)
            POST - http://localhost/api/v1/client = put_CLIENT(args, rdata)
            DELETE - http://localhost/api/v1/configuration/myconfig = delete_CONFIGURATION(args, rdata)
        """
        args = re.sub('/api(/)?', '', self.path).rstrip('/').strip().split('/')

        rdata = None
        rdata_length = self.headers.get('Content-Length', None)
        rdata_format = self.headers.get('Content-Type', None)

        if rdata_length is not None and int(rdata_length) > 0:
            if rdata_format == 'application/json':
                try:
                    rdata = json.loads(self.rfile.read(int(rdata_length)).decode('UTF-8'))
                except ValueError:
                    self.log_message('%s', 'Invalid json rdata detected')

        if self.command in self.api_options:
            version = args[0]
            if version in self.api_versions:
                method_name = f'{self.command.lower()}_{args[1].upper()}'
                if hasattr(self, method_name):
                    method = getattr(self, method_name)
                    method(args, rdata)
                    return
            else:
                self.write_response(
                    400,
                    [('Access-Control-Allow-Origin', '*'), ('Content-Type', 'application/json')],
                    f'{{"versions": {json.dumps(self.api_versions)}}}'
                )
                return
        self.send_error(400, self.responses[400][1])

    def serve_file(self, file_path: str) -> None:
        """Sends a data file as binary to preserve contents, and includes content-type header based on file extension.

        No validation is performed against relative filesystem paths. If additional security is needed, the path should
        be expanded and validated prior to calling this method.

        Args:
            file_path: A local filesystem path.
        """
        try:
            if file_path.endswith(self.file_exts):
                if not pathlib.Path(file_path).absolute().is_file():
                    raise IOError('File does not exist within root path')
                with open(file_path, 'rb') as binary_file:
                    # Only serve specified files. Disable folder browsing
                    self.send_response(200)
                    if file_path.endswith('.html'):
                        self.send_header('Content-Type', 'text/html')
                    elif file_path.endswith('.css'):
                        self.send_header('Content-Type', 'text/css')
                    elif file_path.endswith('.js'):
                        self.send_header('Content-Type', 'text/javascript')
                    elif file_path.endswith('.ttf'):
                        self.send_header('Content-Type', 'application/x-font-ttf')
                    elif file_path.endswith('.map'):
                        self.send_header('Content-Type', 'application/json')
                    else:
                        self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(binary_file.read())
            else:
                raise IOError('File does not exist within root path')
        except IOError:
            self.send_error(404, self.responses[404][1])

    def setup_api(self) -> None:
        """Adds additional API configurations to the handler's base support functions.

        It is recommend to only extend the API options instead of assign new, unless attempting to restrict default
        access.
        """

    def write_response(self, response_code: int, headers: Iterable[Tuple[str, str]], data: str) -> None:
        """Writes an HTTP response back to the socket.

        Args:
            response_code: Valid HTTP response code.
            headers: HTTP header/key value pairs.
            data: Text that will be encoded into bytes as the data payload.
        """
        self.send_response(response_code)
        for header in headers:
            self.send_header(header[0], header[1])
        self.end_headers()
        self.wfile.write(data.encode('utf-8'))


class ApiServer(ThreadingTCPServer, metaclass=abc.ABCMeta):
    """Base multi-threaded HTTP server with user authentication.

    Attributes:
        config: An ApiConfig shared with threads which all requests will access.
        authenticator: An object with authenticate() method to validate user access requests.
    """

    def __init__(self, config: Any, bind_and_activate: bool = True) -> None:
        """Setup the server with user provided config and subclass' authenticator."""
        super(ApiServer, self).__init__((config.host, config.port), config.request_handler, bind_and_activate)
        self.config = config
        self.authenticator = self._init_authenticator()

    @abc.abstractmethod
    def _init_authenticator(self) -> Any:
        """Initializes an object capable of authentication.

        Returns:
            An object with an authenticate() method.
        """

    def authenticate(self, user: str, password: str) -> bool:
        """Validate if a user has access to the server.

        Args:
            user: Text representation of username.
            password: Text representation of the password for the user.

        Returns:
            True if the user passes authentication checks, False if checks fail or no authenticator is found.
        """
        result = False
        if hasattr(self.authenticator, 'authenticate'):
            result = self.authenticator.authenticate(user, password)
        return result


class ApiConfig(object):
    """Configuration information to control the flow of HTTP requests for an API based server.

    Attributes:
        web_root: The base filesystem path to serve files.
        log: The filesystem path to a file to save log lines.
        secure: The filesystem path to an SSL certificate file to enable HTTPS access.
        key: The filesystem path to the SSL certificate key file.
        host: An IP address string to bind the service.
        port: An address port to bind the service.
        debug: Whether to enable debug output for requests.
        authenticator: The filesystem path to the SSL certificate key file.
        thread_handler: An ApiServer class to use when starting a server.
        request_handler: And ApiHandler class to use when processing requests.
    """

    def __init__(self, user_config: dict = None, thread_handler: type = ApiServer, request_handler: type = ApiHandler) -> None:
        """Initializes attributes from a user specified configuration object or defaults.

        Args:
            user_config: User predefined values for initialization.
            thread_handler: Server to use in each handler thread.
            request_handler: Handler to use when processing requests.
        """
        if not user_config:
            user_config = {}
        self.web_root = os.path.abspath(os.path.expanduser(user_config.get('html', 'html')))
        self.log = os.path.abspath(os.path.expanduser(user_config.get('log', 'httpd.log')))
        self.secure = os.path.abspath(os.path.expanduser(user_config.get('cert', 'server.pem')))
        self.key = os.path.abspath(os.path.expanduser(user_config.get('key', 'key.pem')))
        self.host = user_config.get('address', '0.0.0.0')
        self.port = user_config.get('port', 8080)
        self.debug = user_config.get('debug', False)
        self.authenticator = user_config.get('authenticator', None)
        self.thread_handler = thread_handler
        self.request_handler = request_handler
