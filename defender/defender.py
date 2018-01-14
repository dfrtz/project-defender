#! /usr/bin/env python3
"""Primary Application"""

import argparse

from cli import HostShell
from sol.http import *
from sol.secure import AuthDatabase
from sol.secure import AuthServerConfig

MODE_BOTH = 0
MODE_CLIENT = 1
MODE_SERVER = 2

ARGS_MODES = {
    'both': MODE_BOTH,
    'client': MODE_CLIENT,
    'server': MODE_SERVER
}


class DefenderServerConfig(AuthServerConfig):
    def __init__(self, user_config=None):
        super(DefenderServerConfig, self).__init__(user_config)
        self.request_handler = DefenderHandler
        self.db = None
        self.mediad = None
        self.mode = MODE_BOTH


class DefenderHandler(ApiHandler):
    TEMPLATE_VIDEO = b'''
        <html>
            <head></head>
            <body>
                <img src="video"/>
                <video controls="" autoplay="" name="media">
                    <source src="audio" type="audio/x-wav">
                </video>
            </body>
        </html>'''

    def init(self):
        self.api_options = ['GET', 'POST']
        self.api_versions = ['1.0']
        self.api_realm = 'sol-defender'

    def serve_file(self, path):
        config = self.server.config

        if path.endswith('.html'):
            # TODO Show main page
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(self.TEMPLATE_VIDEO)
        elif config.mode in {MODE_CLIENT, MODE_BOTH}:
            if path.endswith('/video'):
                self.send_response(200)
                self.send_header('Connection', 'close')
                self.send_header('Pragma', 'no-store, no-cache')
                self.send_header('Cache-Control',
                                 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
                self.send_header('Expires', '-1')
                self.send_header('Server', 'Python-MJPG-Streamer/0.1')
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=--jpgbound')
                self.end_headers()

                try:
                    config.mediad.send_cv_stream(self)
                except BrokenPipeError:
                    self.log_message('Broken Pipe')
            elif path.endswith('/audio'):
                self.send_response(200)
                self.send_header('Connection', 'close')
                self.send_header('Pragma', 'no-store, no-cache')
                self.send_header('Cache-Control',
                                 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
                self.send_header('Expires', '-1')
                self.send_header('Server', 'Python-WAV-Streamer/0.1')
                self.send_header('Content-Type', 'audio/x-wav')
                self.end_headers()

                try:
                    config.mediad.send_pyaudio(self)
                except BrokenPipeError:
                    self.log_message('Broken Pipe')
        else:
            super(DefenderHandler, self).serve_file(path)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Launch HTTP service and/or shell to control home defense devices.')
    parser.add_argument('-c', '--config',
                        help='Configuration file')
    parser.add_argument('-w', '--web-root',
                        help='Web server root folder')
    parser.add_argument('-l', '--log',
                        help='Log operations to specific file')
    parser.add_argument('-a', '--address',
                        help='Web server bind address')
    parser.add_argument('-p', '--port', type=int,
                        help='Web server bind port')
    parser.add_argument('-s', '--secure',
                        help=('HTTPS certificate. Tip: To generate self signed key and cert, use:\n'
                              'openssl req -newkey rsa:4096 -nodes -keyout key.pem -x509 -days 365 -out certificate.pem'))
    parser.add_argument('-k', '--key',
                        help=('HTTPS key. Tip: To generate self signed key and cert, use:\n'
                              'openssl req -newkey rsa:4096 -nodes -keyout key.pem -x509 -days 365 -out certificate.pem'))
    parser.add_argument('-u', '--user-db',
                        help='User Authentication SQL database.')
    parser.add_argument('-m', '--mode', default='both', choices=['client', 'server', 'both'],
                        help='Application run mode.')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debugging on launch')
    return parser.parse_args()


def main():
    args = parse_args()

    config = {}
    if args.config:
        try:
            with open(args.config) as data_file:
                config = json.load(data_file)
        except ValueError:
            pass
            # self.log_message('Invalid configuration file detected: {}'.format(args.config))
        except FileNotFoundError:
            pass
            # self.log_message('No configuration file found: {}'.format(args.config))
    if not config:
        config = {'server': {}, 'media': {}}

    # Create configurations and assign user defined variables
    if args.web_root:
        config['server']['html'] = args.web_root
    if args.secure:
        config['server']['cert'] = args.secure
    if args.key:
        config['server']['key'] = args.key
    if args.address:
        config['server']['address'] = args.address
    if args.port:
        config['server']['port'] = args.port
    if args.log:
        config['server']['log'] = args.log
    if args.debug:
        config['server']['debug'] = args.debug
    if args.user_db:
        if 'database' not in config['server']:
            config['server']['database'] = {}
        config['server']['database']['user'] = args.user_db
    if args.mode:
        config['server']['mode'] = ARGS_MODES.get(args.mode, MODE_BOTH)

    media_service = None
    http_config = DefenderServerConfig(config.get('server', None))
    http_service = HttpService(http_config)
    http_config.db = AuthDatabase(config['server']['database'].get('user', '~/temp_users.db'))

    # Start services before entering user prompt mode
    http_service.start()
    if http_config.mode in {MODE_CLIENT, MODE_BOTH}:
        import media
        media_config = media.MediaConfig(config.get('media', None))
        media_service = media.MediaService(media_config)
        http_config.mediad = media_service
        media_service.start()

    shell = HostShell()
    shell.set_authdb(http_config.db)
    shell.set_httpd(http_service)
    shell.set_mediad(media_service)
    try:
        while shell.run_command(shell.prompt):
            pass
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, shutting down')

    # Ensure all threads are properly shutdown before exiting main loop
    http_service.shutdown()
    if media_service:
        media_service.shutdown()

    print('Services stopped. Exiting.')


if __name__ == '__main__':
    main()
