#!/usr/bin/env python
"""Primary Application"""

import argparse
import json

from defender.lib.cli import HostShell
from defender.lib.http import ApiConfig
from defender.lib.http import ApiHandler
from defender.lib.http import ApiService
from defender.lib.secure import AuthServer

MODE_BOTH = 0
MODE_CLIENT = 1
MODE_SERVER = 2

ARG_MODES = {
    'both': MODE_BOTH,
    'client': MODE_CLIENT,
    'server': MODE_SERVER
}


class DefenderServerConfig(ApiConfig):
    """Configuration information to control the flow of HTTP requests for an API based server.

    Attributes:
        mediad: A MediaService that all ApiHandlers will have access to while serving API requests.
        mode: An integer representing the current type of options available to handlers from ARG_MODES.
    """

    def __init__(self, user_config=None):
        super(DefenderServerConfig, self).__init__(user_config, thread_handler=AuthServer,
                                                   request_handler=DefenderHandler)
        self.mediad = None
        self.mode = MODE_BOTH


class DefenderHandler(ApiHandler):
    """An HTTPRequestHandler with special access methods to allow streaming media in addition to native API handling."""

    def setup_api(self):
        self.api_options.extend(['POST', 'PUT', 'DELETE'])
        self.api_realm = 'sol-defender'

    SIMPLE_TEMPLATE = b'''
        <html>
            <head></head>
            <body>
                <div>
                    <!--<video controls="" autoplay="" name="media">
                        <source src="audio" type="audio/x-wav">
                    </video>-->
                    <img src="video"/>
                    <audio src="audio" type="audio/x-wav" controls autoplay="autoplay" preload="none">
                </div>
            </body>
        </html>'''

    def serve_file(self, path):
        config = self.server.config

        if path.endswith(self.file_exts):
            # super(DefenderHandler, self).serve_file(path)
            if path.endswith('index.html'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(self.SIMPLE_TEMPLATE)
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
                    config.mediad.send_pyaudio_stream(self)
                except BrokenPipeError:
                    self.log_message('Broken Pipe')
        else:
            super(DefenderHandler, self).serve_file(path)


def load_config(args):
    """Loads a configuration file from local storage and overwrites values with user specified arguments.

    Args:
        args: An argsparse namespace package.

    Returns:
        A dictionary containing user configuration information for all services.
    """
    config = {'server': {}, 'media': {}}
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
        if 'databases' not in config['server']:
            config['server']['databases'] = {}
        config['server']['databases']['users'] = args.user_db
    if args.mode:
        config['server']['mode'] = ARG_MODES.get(args.mode, MODE_BOTH)
    return config


def parse_args():
    parser = argparse.ArgumentParser(description='Launch HTTP service and/or shell to control home defense devices.')
    parser.add_argument('--list-devices', action='store_true', default=False,
                        help='Enable debugging on launch')
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

    config = load_config(args)
    api_config = DefenderServerConfig(config.get('server', {}))

    if api_config.mode in {MODE_CLIENT, MODE_BOTH} or args.list_devices:
        try:
            # Only attempt to load the media libraries if this client is in a mode expected to use OpenCV.
            from defender.lib import media
            if args.list_devices:
                media.MediaService.list_devices()
                return
            media_config = media.MediaConfig(config.get('media', None))
            media_service = media.MediaService(media_config)
        except ImportError as error:
            print('Unable to import media module: {}'.format(error))
            print('Please correct media dependencies or change mode to "server".')
            return
    else:
        media_service = None

    shell = HostShell()
    # Start services after creating shell, but before entering user prompt mode to show banner first
    if media_service:
        media_service.start()
        api_config.mediad = media_service
        shell.mediad = media_service
    api_service = ApiService(api_config)
    api_service.start()
    shell.apid = api_service

    while shell.prompt_user():
        pass

    # Ensure all threads are properly shutdown before exiting main loop
    api_service.shutdown()
    if media_service:
        media_service.shutdown()
    print('Services stopped. Exiting.')


if __name__ == '__main__':
    main()
