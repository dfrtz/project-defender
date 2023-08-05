#!/usr/bin/env python

"""Primary Defender Application."""

import argparse
import json
import time

from defender.lib import cli
from defender.lib import http
from defender.lib import media
from defender.lib import secure

MODE_BOTH = 0
MODE_CLIENT = 1
MODE_SERVER = 2

ARG_MODES = {
    "both": MODE_BOTH,
    "client": MODE_CLIENT,
    "server": MODE_SERVER,
}


class DefenderServerConfig(http.ApiConfig):
    """Configuration information class to control the flow of HTTP requests for an API based server.

    Attributes:
        mediad: Service that all ApiHandlers will have access to while serving API requests.
        mode: Representation of the current type of options available to handlers from ARG_MODES.
    """

    def __init__(self, user_config: dict = None) -> None:
        """Initializes custom server values to add media services to standard API."""
        super(DefenderServerConfig, self).__init__(
            user_config,
            thread_handler=secure.AuthServer,
            request_handler=DefenderHandler,
        )
        # Initialize with a null daemon, this will be updated after it is initialized asynchronously.
        self.mediad = None
        self.mode = MODE_BOTH


class DefenderHandler(http.ApiHandler):
    """An HTTPRequestHandler with special access methods to allow streaming media in addition to native API handling."""

    def setup_api(self) -> None:
        """Enables the base methods allowed for the API and sets the realm for user/password access."""
        self.api_options.extend(["POST", "PUT", "DELETE"])
        self.api_realm = "sol-defender"

    def serve_file(self, path: str) -> None:
        """Overrides the default serve_file behavior to add video/audio endpoints."""
        # Local reference to config for ease of use.
        config = self.server.config

        if path.endswith(self.file_exts):
            # Use default behavior for all files that are not video/audio streams.
            super(DefenderHandler, self).serve_file(path)
        elif config.mode in {MODE_CLIENT, MODE_BOTH}:
            # Running process is also a media server. Provide access to video/audio endpoints.
            if path.endswith("/video"):
                if config.mediad.video_stream is not None:
                    self.send_response(200)
                    self.send_header(
                        "cache-control", "no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0"
                    )
                    self.send_header("connection", "close")
                    self.send_header(
                        "content-type", f"multipart/x-mixed-replace; boundary={config.mediad.config.boundary}"
                    )
                    self.send_header("expires", "-1")
                    self.send_header("pragma", "no-store, no-cache")
                    self.send_header("server", "python-mjpeg-streamer/0.1")
                    self.send_header("x-starttime", time.time())
                    self.end_headers()
                    try:
                        config.mediad.send_cv_stream(self)
                    except BrokenPipeError:
                        self.log_message("Broken Pipe")
                else:
                    self.send_response(503)
            elif path.endswith("/audio"):
                if config.mediad.audio_stream is not None:
                    self.send_response(200)
                    self.send_header(
                        "cache-control", "no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0"
                    )
                    self.send_header("connection", "close")
                    self.send_header("content-type", "audio/x-wav")
                    self.send_header("expires", "-1")
                    self.send_header("pragma", "no-store, no-cache")
                    self.send_header("server", "python-wav-streamer/0.1")
                    self.end_headers()
                    try:
                        config.mediad.send_pyaudio_stream(self)
                    except BrokenPipeError:
                        self.log_message("Audio endpoint encountered broken pipe")
                else:
                    self.send_response(503)
        else:
            super(DefenderHandler, self).serve_file(path)


def load_config(args: argparse.Namespace) -> dict:
    """Loads a configuration file from local storage and overwrites values with user specified arguments.

    Args:
        args: User customization arguments.

    Returns:
        A dictionary containing user configuration information for all services.
    """
    config = {"server": {}, "media": {}}
    if args.config:
        try:
            with open(args.config) as data_file:
                config = json.load(data_file)
        except ValueError:
            print(f"Invalid configuration file detected: {args.config}")
        except FileNotFoundError:
            print(f"No configuration file found: {args.config}")

    # Create configurations and assign user defined variables
    if args.web_root:
        config["server"]["html"] = args.web_root
    if args.secure:
        config["server"]["cert"] = args.secure
    if args.key:
        config["server"]["key"] = args.key
    if args.address:
        config["server"]["address"] = args.address
    if args.port:
        config["server"]["port"] = args.port
    if args.log:
        config["server"]["log"] = args.log
    if args.debug:
        config["server"]["debug"] = args.debug
    if args.user_db:
        if "databases" not in config["server"]:
            config["server"]["databases"] = {}
        config["server"]["databases"]["users"] = args.user_db
    if args.mode:
        config["server"]["mode"] = ARG_MODES.get(args.mode, MODE_BOTH)
    return config


def parse_args() -> argparse.Namespace:
    """Parses user arguments for primary defender application."""
    parser = argparse.ArgumentParser(description="Launch HTTP service and/or shell to control home defense devices.")
    parser.add_argument("--list-devices", action="store_true", default=False, help="Enable debugging on launch")
    parser.add_argument("-c", "--config", help="Configuration file")
    parser.add_argument("-w", "--web-root", help="Web server root folder")
    parser.add_argument("-l", "--log", help="Log operations to specific file")
    parser.add_argument("-a", "--address", help="Web server bind address")
    parser.add_argument("-p", "--port", type=int, help="Web server bind port")
    parser.add_argument(
        "-s",
        "--secure",
        help=(
            "HTTPS certificate. Tip: To generate self signed key and cert, use:\n"
            "openssl req -newkey rsa:4096 -nodes -keyout key.pem -x509 -days 365 -out certificate.pem"
        ),
    )
    parser.add_argument(
        "-k",
        "--key",
        help=(
            "HTTPS key. Tip: To generate self signed key and cert, use:\n"
            "openssl req -newkey rsa:4096 -nodes -keyout key.pem -x509 -days 365 -out certificate.pem"
        ),
    )
    parser.add_argument("-u", "--user-db", help="User Authentication SQL database.")
    parser.add_argument("-m", "--mode", default="both", choices=list(ARG_MODES.keys()), help="Application run mode.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debugging on launch")
    return parser.parse_args()


def main() -> None:
    """Main execution for Defender 'defend' application.

    Summary of application flow:
        1. Parse user arguments into a config dictionary to send to daemons.
        2. Load OpenCV/media libraries and start media daemon if in a client (camera) mode.
        3. Load API service to handle serving files and/or media streams.
        3. Create user shell and handle input until exited.
    """
    args = parse_args()
    config = load_config(args)
    api_config = DefenderServerConfig(config.get("server", {}))

    # Attempt to load the media libraries if this client is in a mode expected to use OpenCV.
    if api_config.mode in {MODE_CLIENT, MODE_BOTH} or args.list_devices:
        if args.list_devices:
            media.AudioStream.list_devices()
            media.VideoStream.list_devices()
            return
        media_config = media.MediaConfig(config.get("media", None))
        media_service = media.MediaService(media_config)
    else:
        media_service = None

    # Start services after creating shell, but before entering user prompt mode to show banner first
    shell = cli.HostShell()
    if media_service:
        media_service.start()
        api_config.mediad = media_service
        shell.mediad = media_service
    api_service = http.ApiService(api_config)
    api_service.start()
    shell.apid = api_service

    while shell.prompt_user():
        # Loop until user requests exit.
        pass

    # Ensure all threads are properly shutdown before exiting main loop
    api_service.shutdown()
    if media_service:
        media_service.shutdown()
    print("Services stopped. Exiting.")


if __name__ == "__main__":
    main()
