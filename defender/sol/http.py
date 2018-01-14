import base64
import json
import logging
import logging.handlers
import os
import re
import socket
import ssl
import threading

from http.server import BaseHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingTCPServer


class ApiConfig(object):
    def __init__(self, user_config=None):
        if not user_config:
            user_config = {}
        self.web_root = os.path.abspath(os.path.expanduser(user_config.get('html', 'html')))
        self.log = os.path.abspath(os.path.expanduser(user_config.get('log', 'httpd.log')))
        self.secure = os.path.abspath(os.path.expanduser(user_config.get('cert', 'server.pem')))
        self.key = os.path.abspath(os.path.expanduser(user_config.get('key', 'key.pem')))
        self.host = user_config.get('address', '0.0.0.0')
        self.port = user_config.get('port', 8080)
        self.debug = user_config.get('debug', False)
        self.thread_handler = ApiServer
        self.request_handler = ApiHandler


class HttpService(object):
    def __init__(self, config):
        self.config = config
        self._thread = None

        self.logger = logging.getLogger(__name__)
        self.setup_logger(self.config.log)

    def setup_logger(self, log):
        if not len(self.logger.handlers):
            formatter = logging.Formatter(fmt='{asctime} - {levelname} - {message}', datefmt='%Y-%m-%dT%H:%M:%S.%s',
                                          style='{')
            file_handler = logging.handlers.RotatingFileHandler(log, maxBytes=10000000, backupCount=5, encoding='UTF-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)

    def log_message(self, message, external=False, level=logging.INFO):
        self.logger.log(level, message)

        if external:
            print(message)

    def set_debug(self, enabled=False):
        self.shutdown()
        if enabled:
            self.log_message('HTTP service enabling debugging', True)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.log_message('HTTP service disabling debugging', True)
            self.logger.setLevel(logging.INFO)
        self.start()

    def start(self):
        if self._thread is None:
            self.log_message('HTTP service starting', True)
            self._thread = self.config.thread_handler(self.config, False)

            # Manually bind and activate to set socket reuse w/o overriding class
            self._thread.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._thread.server_bind()
            self._thread.server_activate()

            # Wrap HTTPD socket in SSL if a certificate was provided
            cert_loaded = False
            if self.config.secure:
                cert_file = Path(os.path.abspath(self.config.secure))
                if cert_file.is_file():
                    # TODO: Validate certificate
                    self.log_message('HTTP service loading SSL cert: {}'.format(self.config.secure), True)
                    self._thread.socket = ssl.wrap_socket(self._thread.socket, keyfile=self.config.key,
                                                          certfile=self.config.secure, server_side=True,
                                                          ssl_version=ssl.PROTOCOL_TLSv1_2)
                    cert_loaded = True
            # Start HTTPD in new thread to prevent blocking user input
            threading.Thread(target=self._thread.serve_forever).start()

            self.log_message('HTTP service listening on {}://{}:{}'.format(
                ('https' if cert_loaded else 'http'), self.config.host, self.config.port), True)
        else:
            self.log_message('HTTP service cannot start, already listening', True)

    def shutdown(self):
        if self._thread is not None:
            self.log_message('HTTP service shutting down', True)
            self._thread.socket.close()
            self._thread.shutdown()
            self._thread = None
            self.log_message('HTTP service offline', True)
        else:
            self.log_message('HTTP service offline. Aborting repeat shutdown.', True)


class ApiServer(ThreadingTCPServer):
    def __init__(self, config, bind_and_activate=True):
        super(ApiServer, self).__init__((config.host, config.port), config.request_handler, bind_and_activate)
        self.config = config
        self.users = {
            # Default user is default:default
            'default': {'password': 'default'}
        }

    def authenticate(self, user, password):
        authorized = False
        if user in self.users:
            if password == self.users[user]['password']:
                authorized = True
        return authorized


class ApiHandler(BaseHTTPRequestHandler):
    file_exts = ('.css', '.html', '.js', '.ttf', '.map')

    def __init__(self, *args):
        # Set default HTTP response options
        self.api_options = ['GET']
        self.api_versions = ['1.0']
        self.api_headers = ['Content-Type']
        self.api_realm = 'secret'

        # Call child HTTP response setup
        if hasattr(self, 'init'):
            self.init()

        self.logger = logging.getLogger(__name__)

        # Init must be last, or handle response will be called without user configuration
        super(ApiHandler, self).__init__(*args)

    def log_message(self, template, *args):
        self.logger.info('{} - {}'.format(self.client_address[0], template % args))

    def authenticate(self):
        if not hasattr(self.server, 'authenticate'):
            self.log_message('%s', 'Using auth handler without auth server, skipping authorization')
            return True

        header = self.headers.get('Authorization', None)
        if header is None:
            self.do_AUTHHEAD()
            return False

        # Split header into [Basic] and [username:password]
        headers = header.split()
        if len(headers) < 2 or headers[0] != 'Basic':
            self.do_AUTHHEAD()
            return False

        userpass = base64.b64decode(headers[1].encode()).decode().split(':')
        user = userpass[0]
        password = userpass[1]

        authenticated = self.server.authenticate(user, password)

        if not authenticated:
            self.do_AUTHHEAD()

        return authenticated

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', ','.join(self.api_options))
        self.send_header('Access-Control-Allow-Headers', ','.join(self.api_headers))
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401, self.responses[401][1])
        self.send_header('WWW-Authenticate', 'Basic realm="{}"'.format(self.api_realm))
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Authentication Failed')

    def do_GET(self):
        if self.path.startswith('/api'):
            args = re.sub('/api(/)?', '', self.path).rstrip('/').split('/')

            if len(args) < 2 or args[0] == '':
                # Bypass authentication if only checking versions
                self.write_response(200,
                                    [('Access-Control-Allow-Origin', '*'), ('Content-Type', 'application/json')],
                                    '{{"versions": {}}}'.format(json.dumps(self.api_versions)))
                return

            if not self.authenticate():
                return

            self.serve_api()
        else:
            if not self.authenticate():
                return

            path = self.path

            if path == '/':
                path = '{}/index.html'.format(self.server.config.web_root)
            else:
                path = self.server.config.web_root + path

            if os.path.abspath(path).startswith(self.server.config.web_root):
                # Only serve files under application root or user specified location
                self.serve_file(path)
            else:
                self.send_error(404, self.responses[404][1])

    def do_POST(self):
        if not self.authenticate():
            return

        if self.path.startswith('/api'):
            self.serve_api()
        else:
            self.send_error(400, self.responses[400][1])

    def do_PUT(self):
        if not self.authenticate():
            return

        if self.path.startswith('/api'):
            self.serve_api()
        else:
            self.send_error(400, self.responses[400][1])

    def serve_api(self):
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
                method_name = '{}_{}'.format(self.command.lower(), args[1].upper())
                if hasattr(self, method_name):
                    method = getattr(self, method_name)
                    method(args, rdata)
                    return
            else:
                self.write_response(400, [('Access-Control-Allow-Origin', '*'), ('Content-Type', 'application/json')],
                                    '{{"versions": {}}}'.format(json.dumps(self.api_versions)))
                return

        self.send_error(400, self.responses[400][1])

    def serve_file(self, path):
        try:
            if path.endswith(self.file_exts):
                # Only serve specified files. Disable folder browsing
                self.send_response(200)

                if path.endswith('.html'):
                    self.send_header('Content-Type', 'text/html')
                elif path.endswith('.css'):
                    self.send_header('Content-Type', 'text/css')
                elif path.endswith('.js'):
                    self.send_header('Content-Type', 'text/javascript')
                elif path.endswith('.ttf'):
                    self.send_header('Content-Type', 'application/x-font-ttf')
                elif path.endswith('.map'):
                    self.send_header('Content-Type', 'application/json')
                else:
                    self.send_header('Content-Type', 'text/plain')

                self.end_headers()

                # Send file as binary to keep formatting and line breaks
                binary_file = open(path, 'rb')
                self.wfile.write(binary_file.read())
                binary_file.close()

                return
            else:
                raise IOError('File does not exist within root path')
        except IOError:
            self.send_error(404, self.responses[404][1])

    def write_response(self, response_code, headers, data):
        self.send_response(response_code)
        for header in headers:
            self.send_header(header[0], header[1])
        self.end_headers()
        self.wfile.write(data.encode('utf-8'))
