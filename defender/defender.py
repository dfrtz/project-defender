#! /usr/bin/python3
"""Primary Application"""

import argparse
import json
import re
import time

from cli import HostShell
from sol.http import *
from sol.secure import AuthDatabase
from sol.secure import AuthServerConfig


class DefenderServerConfig(AuthServerConfig):
    def __init__(self):
        super(DefenderServerConfig, self).__init__()

        self.request_handler = DefenderHandler
        self.db = None


class DefenderHandler(ApiHandler):
    file_exts = ('.css', '.html', '.js', '.json', '.ttf', '.map')

    def init(self):
        self.api_options = ['GET', 'POST', 'PUT']
        self.api_versions = ['1.0']
        self.api_realm = 'sol-defender'

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
                path = os.path.abspath('{}/index.html'.format(self.server.config.web_root))
            else:
                path = os.path.abspath('{}{}'.format(self.server.config.web_root, path))

            # Only serve files under application root or user specified location
            if path.startswith(os.path.abspath(self.server.config.web_root)):
                self.serve_file(os.path.abspath(path))
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
                self.write_response(400,
                                    [('Access-Control-Allow-Origin', '*'), ('Content-Type', 'application/json')],
                                    '{{"versions": {}}}'.format(json.dumps(self.api_versions)))
                return

        self.send_error(400, self.responses[400][1])


def get_date_time_string():
    now = time.time()
    year, month, day, hour, minute, second = time.localtime(now)
    time_string = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(year, month, day, hour, minute, second)
    return time_string


def parse_args():
    parser = argparse.ArgumentParser(
        description='Launch HTTP server and shell to control home defense devices')
    parser.add_argument("-w", "--web-root", help="Web server root folder. Default = ./html")
    parser.add_argument("-l", "--log", help="Log operations to file")
    parser.add_argument("-a", "--address", help="Web server bind address")
    parser.add_argument("-p", "--port", help="Web server bind port", type=int)
    parser.add_argument("-s", "--secure",
                        help="HTTPS certificate. Tip: To generate self signed, use: openssl req -newkey rsa:4096 -nodes -keyout key.pem -x509 -days 365 -out certificate.pem")
    parser.add_argument("-u", "--user-db", help="User Authentication SQL database.", default='user_auth.db')
    parser.add_argument("-d", "--debug", help="Enable debugging on launch", action='store_true')

    return parser.parse_args()


def main():
    args = parse_args()

    shell = HostShell()
    http_config = DefenderServerConfig()
    http_service = HttpService(http_config)

    # Create configurations and assign user defined variables
    if args.web_root:
        http_config.web_root = os.path.abspath(args.web_root)
    if args.secure:
        http_config.secure = args.secure
    if args.address:
        http_config.host = args.address
    if args.port:
        http_config.port = args.port
    if args.log:
        http_config.log = args.log
    if args.debug:
        http_config.debug = args.debug

    authdb = AuthDatabase(os.path.abspath(args.user_db))

    http_config.db = authdb

    shell.set_authdb(authdb)
    shell.set_httpd(http_service)

    # Start services before entering user prompt mode
    http_service.start()

    try:
        while shell.run_command(shell.prompt):
            pass
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, shutting down')

    # Ensure all threads are properly shutdown before exiting main loop
    http_service.shutdown()

    print('Services stopped. Exiting.')


if __name__ == "__main__":
    main()
