#! /usr/bin/python3
"""Primary Application"""

import argparse

from cli import HostShell
from sol.http import *
from sol.secure import AuthDatabase
from sol.secure import AuthServerConfig
import time

MODE_BOTH = 0
MODE_CLIENT = 1
MODE_SERVER = 2

MODES = {
    'both': MODE_BOTH,
    'client': MODE_CLIENT,
    'server': MODE_SERVER
}


class DefenderServerConfig(AuthServerConfig):
    def __init__(self):
        super(DefenderServerConfig, self).__init__()

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
        # TODO Check if in server or client mode

        if path.endswith('.html'):
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
                except BrokenPipeError as e:
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
                except BrokenPipeError as e:
                    self.log_message('Broken Pipe')
        else:
            super(DefenderHandler, self).serve_file(path)


def get_date_time_string():
    now = time.time()
    year, month, day, hour, minute, second = time.localtime(now)
    time_string = '{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}'.format(year, month, day, hour, minute, second)
    return time_string


def parse_args():
    parser = argparse.ArgumentParser(
        description='Launch HTTP service and/or shell to control home defense devices.')
    parser.add_argument('-w', '--web-root', help='Web server root folder. Default = ./html')
    parser.add_argument('-l', '--log', help='Log operations to file')
    parser.add_argument('-a', '--address', help='Web server bind address')
    parser.add_argument('-p', '--port', help='Web server bind port', type=int)
    parser.add_argument('-s', '--secure',
                        help='HTTPS certificate. Tip: To generate self signed, use: openssl req -newkey rsa:4096 -nodes -keyout key.pem -x509 -days 365 -out certificate.pem')
    parser.add_argument('-u', '--user-db', help='User Authentication SQL database.', default='user_auth.db')
    parser.add_argument('-m', '--mode', help='Application run mode.', choices=['client', 'server', 'both'],
                        default='both')
    parser.add_argument('-c', '--camera', help='Camera device id when running in client mode')
    parser.add_argument('-d', '--debug', help='Enable debugging on launch', action='store_true')

    return parser.parse_args()


def main():
    args = parse_args()

    shell = HostShell()
    http_config = DefenderServerConfig()
    http_service = HttpService(http_config)
    media_service = None

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

    if args.mode:
        http_config.mode = MODES.get(args.mode, MODE_BOTH)

    authdb = AuthDatabase(os.path.abspath(args.user_db))
    http_config.db = authdb
    shell.set_authdb(authdb)
    shell.set_httpd(http_service)
    shell.set_mediad(media_service)

    # Start services before entering user prompt mode
    http_service.start()
    if http_config.mode in {MODE_CLIENT, MODE_BOTH}:
        import media
        media_config = media.MediaConfig()
        media_service = media.MediaService(media_config)
        http_config.mediad = media_service

        if args.camera:
            media_config.camera_dev = int(args.camera)

        media_service.start()

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
