"""Audio/Video manipulation and services."""

import base64
import ctypes
import logging
import logging.handlers
import os
import random
import string
import threading
import time
import wave
from contextlib import contextmanager
from io import BytesIO
from io import StringIO
from typing import Any
from typing import Tuple

try:
    import cv2
    import pyaudio
    from PIL import Image
except ImportError as error:
    logging.error(f'Unable to import media module; correct media dependencies or change mode to "server": {error}')

# Error handler taken from: alsa-lib.git include/error.h
# typedef void (*snd_lib_error_handler_t)(const char *file, int line, const char *function, int err, const char *fmt)
ALSA_ERR_HANDLER = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
DEFAULT_BOUNDARY = "jpgboundary"
CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits
NO_STREAM = -1


class LogService(object):
    """Base service class which allows logging to a file and output.

    Attribute:
        logger: A logging object to write messages out to storage.
    """

    def __init__(self, logger: logging.Logger) -> None:
        """Set up the service with a given logger."""
        self.logger = logger

    def log_message(self, message: str, external: bool = False, level: int = logging.INFO) -> None:
        """Logs a message to storage and to output visible to users.

        Args:
            message: The message to save and display.
            external: Whether the message is visible to user.
            level: Level used to determine the severity of the message.
        """
        if self.logger:
            self.logger.log(level, message)
        if external:
            print(message)


class VideoConfig(object):
    """Configuration information to control video streams.

    Attributes:
        device: Device index of the video input to open.
        width: Width of the images captures in pixels.
        height: Height of the images captures in pixels.
        framerate: Maximum amount of images to capture per second.
        quality: Image quality after compression between 0-100.
    """

    DEVICE = 0
    WIDTH = 640
    HEIGHT = 480
    FRAMERATE = 30
    QUALITY = 85

    def __init__(self, config: dict = None) -> None:
        """Initializes attributes from a user specified configuration object or defaults.

        Args:
            config: User predefined values for initialization.
        """
        if not config:
            config = {}
        self.enabled = config.get("enabled", False)
        self.device = config.get("device", VideoConfig.DEVICE)
        self.width = config.get("width", VideoConfig.WIDTH)
        self.height = config.get("height", VideoConfig.HEIGHT)
        self.framerate = config.get("fps", VideoConfig.FRAMERATE)
        self.quality = config.get("quality", VideoConfig.QUALITY)


class VideoStream(LogService):
    """Streaming service to pull data from a video input device and serve to multiple requesters.

    Attributes:
        config: A VideoConfig containing information for the stream.
    """

    def __init__(self, config: VideoConfig, logger: logging.Logger = None) -> None:
        """Initialize the stream with custom config and null image."""
        super(VideoStream, self).__init__(logger)
        self._image = None
        self._last_read = None
        self._stop_event = threading.Event()
        self._stop_event.set()
        self.config = config

    @staticmethod
    def list_devices() -> None:
        """Provide a list of all available video devices indexes to user."""
        print("Video Devices:")
        arr = []
        for index in range(50):
            stream = cv2.VideoCapture(index)
            if stream.isOpened():
                arr.append(index)
                stream.release()
        print(arr)

    def start(self) -> Any:
        """Creates the background capture thread to read images from the input asynchronously.

        Returns:
            Self for chaining calls.
        """
        if self._stop_event.is_set():
            self._stop_event.clear()
            self.log_message("Video stream starting.", True)
            threading.Thread(target=self.process_stream, args=()).start()
        else:
            self.log_message("Video stream cannot start, already capturing.", True)
        return self

    def process_stream(self, heartbeat_interval: int = 1) -> None:
        """Initializes video stream for continuous access until service is stopped.

        Args:
            heartbeat_interval: How often to check for an open device in seconds.
        """
        stream = None
        while not self._stop_event.is_set():
            stream = cv2.VideoCapture(self.config.device)
            if self.config.width:
                stream.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            if self.config.height:
                stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            if stream.isOpened():
                break
            self.log_message(f"Video stream could not open, retrying in {heartbeat_interval} seconds.", True)
            time.sleep(heartbeat_interval)

        if stream is not None:
            self.log_message("Video stream running.", True)
            while stream.isOpened() and not self._stop_event.is_set():
                captured, image = stream.read()
                if captured:
                    # Update the internal image, this will be sent to the streams.
                    self._image = image
                    self._last_read = time.time()
            # Release the stream and saved image to free up memory.
            stream.release()
            self._image = None
            self.log_message("Video stream stopped.", True)

    def read(self) -> Tuple[bytes, int]:
        """Provides the most recently captured image.

        Returns:
            A bytes like object representing the most recently captured image, and time of capture in nanoseconds.
        """
        return self._image, self._last_read

    def stop(self) -> None:
        """Signals the background capture thread to stop reading images."""
        if not self._stop_event.is_set():
            self.log_message("Video stream stopping.", True)
            self._stop_event.set()
        else:
            self.log_message("Video stream offline. Aborting repeat shutdown.", True)


class AudioConfig(object):
    """Configuration information to control audio streams.

    Attributes:
        device: An string name or integer index of the audio input device to open.
        chunk: An integer for the amount of samples to pull from the audio stream at one time for processing.
        format: An integer representing the format of of the audio stream.
        channels: An integer representing the desired number of input channels to capture.
        framerate: An integer representing the desired rate (in Hz)
    """

    DEVICE = 0
    CHUNK = 8192
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100

    def __init__(self, config: dict = None) -> None:
        """Initializes attributes from a user specified configuration object or defaults.

        Args:
            config: User predefined values for initialization.
        """
        if not config:
            config = {}
        self.enabled = config.get("enabled", False)
        self.device = config.get("device", AudioConfig.DEVICE)
        self.chunk = config.get("chunk", AudioConfig.CHUNK)
        self.format = AudioConfig.FORMAT
        self.channels = config.get("channels", AudioConfig.CHANNELS)
        self.framerate = config.get("rate", AudioConfig.RATE)


class AudioStream(LogService):
    """Streaming service to pull data from an audio input device and serve to multiple requesters.

    Attributes:
        config: An Audio containing information for the stream.
        header: A base64 encoded byte string representing the beginning of an audio file.
    """

    def __init__(self, config: AudioConfig, logger: logging.Logger = None) -> None:
        """Initialize the stream with custom config and null header."""
        super(AudioStream, self).__init__(logger)
        self._chunk = None
        self._chunk_index = NO_STREAM
        self._stream = None
        self._stop_event = threading.Event()
        self._stop_event.set()
        self.config = config
        self.header = ""

    @staticmethod
    def _c_error_handler(file: str, line: int, function_name: str, err: int, fmt: str) -> None:
        """Handles an error message from C based libraries."""
        # Error handler reference taken from: alsa-lib.git include/error.h
        # typedef void (*snd_lib_error_handler_t)(const char *file, int line, const char *function, int err, const char *fmt)

    def _process_stream(self, heartbeat_interval: int = 1) -> None:
        """Initializes audio stream for continuous access until service is stopped.

        Args:
            heartbeat_interval: How often to check for an open device in seconds.
        """
        self.header = AudioStream.mk_wav_header(self.config.channels, self.config.format, self.config.framerate)
        chunk_size = self.config.chunk
        try:
            # Find the correct device ID.
            dev_id = 0
            device_found = False
            audio = None
            while not self._stop_event.is_set():
                # Hide the error spam while trying to open the audio stream
                with AudioStream.hide_c_errors("libasound.so"):
                    audio = pyaudio.PyAudio()
                # Loop over every device until the match is found. Indexes and names may or may not exist.
                for index in range(audio.get_device_count()):
                    dev = audio.get_device_info_by_index(index)
                    if isinstance(self.config.device, int):
                        if self.config.device == dev["index"]:
                            device_found = True
                            break
                    # Indexes are not as reliable, allow a name string to be used instead.
                    if isinstance(self.config.device, str):
                        if self.config.device in dev["name"]:
                            dev_id = dev["index"]
                            device_found = True
                            break
                if device_found:
                    break
                # Close the audio device, a connection could not be made.
                audio.terminate()
                self.log_message(f"Audio stream could not open device, retrying in {heartbeat_interval} seconds.", True)
                time.sleep(heartbeat_interval)

            if audio is None:
                # Open the stream only if a device ID was found
                self._stream = audio.open(
                    format=self.config.format,
                    channels=self.config.channels,
                    rate=self.config.framerate,
                    input=True,
                    input_device_index=dev_id,
                    frames_per_buffer=chunk_size,
                )

                self.log_message("Audio stream running.", True)
                try:
                    while self._stream.is_active() and not self._stop_event.is_set():
                        data = self._stream.read(chunk_size, False)
                        if len(data):
                            self._chunk = data
                            # Cycle audio chunk index to reflect data is new
                            self._chunk_index = self._chunk_index + 1
                            if self._chunk_index > 100:
                                self._chunk_index = 0
                except OSError as error:
                    self.log_message(f"process_stream - low level error - {error}", True, level=logging.ERROR)

                self._chunk = None
                self._chunk_index = NO_STREAM
                self._stream.stop_stream()
                self._stream.close()
                audio.terminate()
                self.log_message("Audio stream stopped.", True)
        except OSError as error:
            self.log_message(f"process_stream - high level - error {error}", True, level=logging.ERROR)

    @staticmethod
    @contextmanager
    def hide_c_errors(lib_file: str) -> None:
        """Sets a temporary error handler for a C based library.

        Args:
            lib_file: A library file name. Example: 'libasound.so'
        """
        lib = ctypes.cdll.LoadLibrary(lib_file)
        lib.snd_lib_error_set_handler(ALSA_ERR_HANDLER(AudioStream._c_error_handler))
        yield
        lib.snd_lib_error_set_handler(None)

    @staticmethod
    def gen_lock_id() -> str:
        """Creates a random ID used to lock streams and prevent releasing data in transit."""
        id = "".join(random.choice(CHARS) for _ in range(16))
        return id

    @staticmethod
    def list_devices() -> None:
        """Provide a list of all available audio devices and details to user."""
        print("Audio Devices:")
        with AudioStream.hide_c_errors("libasound.so"):
            p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            for key, value in dev.items():
                print("{:<25} {}".format(key + ":", value))
            print()
        p.terminate()
        print()

    @staticmethod
    def mk_wav_header(channels: int, audio_format: int, framerate: int) -> bytes:
        """Creates header information for a WAV file.

        Args:
            channels: Desired number of input channels to capture.
            audio_format: Format of of the audio stream.
            framerate: The desired rate (in Hz).

        Returns:
            A bytes like object representing the encoding for an audio file.
        """
        with BytesIO() as memory_file, wave.open(memory_file, "w") as wave_file:
            wave_file.setnchannels(channels)
            wave_file.setsampwidth(pyaudio.get_sample_size(audio_format))
            wave_file.setframerate(framerate)
            wave_file.writeframes(b"")
            encoding = base64.encodebytes(memory_file.getvalue())
        return encoding

    def read(self) -> Tuple[int, bytes]:
        """Provides the most recently captured audio chunk data.

        Returns:
            A tuple with index of audio stream to determine if data is new, and bytes like object representing the most
            recently captured audio chunk, or (-1, None) if no audio is available.
        """
        data = self._chunk_index, self._chunk
        return data

    def start(self) -> Any:
        """Creates the background capture thread to listen for audio from the input asynchronously.

        Returns:
            Self for chaining calls.
        """
        if self._stop_event.is_set():
            self._stop_event.clear()
            self.log_message("Audio stream starting.", True)
            threading.Thread(target=self._process_stream, args=()).start()
        else:
            self.log_message("Audio stream cannot start, already capturing.", True)
        return self

    def stop(self) -> None:
        """Signals the background capture thread to stop listening for audio."""
        if not self._stop_event.is_set():
            self.log_message("Audio stream stopping.", True)
            self._stop_event.set()
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
        else:
            self.log_message("Audio stream offline. Aborting repeat shutdown.", True)


class MediaConfig(object):
    """Configuration information to control a group of audio and video streams.

    Attributes:
        video: A VideoConfig containing information for video input devices.
        audio: An AudioConfig containing information for audio input devices.
        log: A string path to storage where logging messages will be stored.
        debug: A boolean representing whether the service is in debugging mode.
    """

    def __init__(self, config: dict = None) -> None:
        """Initializes attributes from a user specified configuration object or defaults.

        Args:
            config: User predefined values for initialization.
        """
        if not config:
            config = {}
        self.video = VideoConfig(config.get("video", None))
        self.audio = AudioConfig(config.get("audio", None))
        self.log = os.path.abspath(os.path.expanduser(config.get("log", "media.log")))
        self.debug = False
        self.boundary = config.get("boundary", DEFAULT_BOUNDARY)


class MediaService(LogService):
    """Service to control flow of multiple audio and video streams, and relay captured data to a external handlers.

    Attributes:
        _stop_event: A threading.Event() used to control start and stop operations on the services.
        config: A MediaConfig containing information for audio and video streams.
        video_stream: A VideoStream service pulling data from a video input device.
        audio_stream: An AudioStream service pulling data from a audio input device.
        hog: A CV HOGDescriptor (histogram of oriented gradients) used to perform image post processing.
    """

    def __init__(self, config: MediaConfig) -> None:
        """Setup the service will null streams."""
        super(MediaService, self).__init__(logging.getLogger(__name__))
        self.config = config
        self.video_stream = None
        self.audio_stream = None
        self.hog = cv2.HOGDescriptor()
        self._stop_event = threading.Event()
        self._stop_event.set()
        self.setup_logger(config.log)

        # Cache the byte string for image boundaries to prevent recreating every frame.
        self._image_boundary = f"\r\n--{self.config.boundary}\r\n".encode()

    def set_debug(self, enabled: bool = False) -> None:
        """Enables or disables debug output from the server.

        This method is disruptive while the setting is being applied.

        Args:
            enabled: A boolean representing whether debug mode should be enabled.
        """
        self.shutdown()
        if enabled:
            self.log_message("Media service enabling debugging", True)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.log_message("Media service disabling debugging", True)
            self.logger.setLevel(logging.INFO)
        self.start()

    def setup_logger(self, log: str) -> None:
        """Creates a logger to record the lifecycle of the server."""
        if not len(self.logger.handlers):
            formatter = logging.Formatter(
                fmt="{asctime} - {levelname} - {message}", datefmt="%Y-%m-%dT%H:%M:%S.%s", style="{"
            )
            file_handler = logging.handlers.RotatingFileHandler(log, maxBytes=10000000, backupCount=5, encoding="UTF-8")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)

    def shutdown(self) -> None:
        """Stops the audio and video server threads and prevents serving new handler requests."""
        if not self._stop_event.is_set():
            self._stop_event.set()
            self.log_message("Media service shutting down", True)
            self.stop_video()
            self.stop_audio()
            self.log_message("Media service offline", True)
        else:
            self.log_message("Media service offline. Aborting repeat shutdown.", True)

    def start(self) -> None:
        """Creates the audio and video server threads to service new handler requests."""
        if self._stop_event.is_set():
            self._stop_event.clear()

        self.log_message("Media service starting", True)
        self.start_video()
        self.start_audio()
        self.log_message("Media service started.")

    def start_audio(self) -> None:
        """Creates the audio server thread to service new handler requests."""
        if self.config.audio.enabled:
            self.audio_stream = AudioStream(self.config.audio, self.logger).start()
        else:
            self.log_message(
                f"Skipping audio. Enabled: {self.config.audio.enabled} Running: {self.audio_stream is not None}", True
            )

    def start_video(self) -> None:
        """Creates the video server thread to service new handler requests."""
        if self.config.video.enabled and self.video_stream is None:
            self.video_stream = VideoStream(self.config.video, self.logger).start()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        else:
            self.log_message(
                f"Skipping video. Enabled: {self.config.video.enabled} Running: {self.video_stream is not None}", True
            )

    def stop_audio(self) -> None:
        """Stops the audio server thread to prevent handling new requests."""
        if self.audio_stream is not None:
            self.audio_stream.stop()
            self.audio_stream = None
        else:
            self.log_message("Audio not running, skipping shutdown.", True)

    def stop_video(self) -> None:
        """Stops the video server thread to prevent handling new requests."""
        if self.video_stream is not None:
            self.video_stream.stop()
            self.video_stream = None
        else:
            self.log_message("Video not running, skipping shutdown.", True)

    def write_image(self, handler: Any, image: bytes) -> None:
        """Writes a single image to an external handler.

        Args:
            handler: An external service handler where the image will be relayed.
            image: A bytes like object representing an image.
        """
        handler.wfile.write(self._image_boundary)
        handler.send_header("content-type", "image/jpeg")
        handler.send_header("content-length", len(image))
        handler.send_header("x-timestamp", time.time())
        handler.end_headers()
        try:
            handler.wfile.write(image)
        except ConnectionResetError as error:
            # Only record errors that are not the result of a client closing the connection mid-write (104).
            if error.errno != 104:
                self.log_message(f"Connection reset {error}", True)

    def send_cv_detection_stream(self, handler: Any) -> None:
        """Opens a continuous stream to send Computer Vision processed images with various object detection models.

        Args:
            handler: An external service handler where the image will be relayed.
        """
        interval = 1 / self.config.video.framerate
        quality = self.config.video.quality
        while not self._stop_event.is_set():
            frame, timestamp = self.video_stream.read()
            if frame is not None:
                rects, weights = self.hog.detectMultiScale(frame, winStride=(4, 4), padding=(8, 8), scale=1.05)
                for x, y, w, h in rects:
                    # Create rectangles on the image if detection is being used.
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                encoded, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                if encoded:
                    self.write_image(handler, jpeg.tobytes())
            time.sleep(interval)

    def send_cv_pil_stream(self, handler: Any) -> None:
        """Opens a continuous stream to send Computer Vision processed images using Python Imaging Library (PIL).

        Current testing has shown this method of processing to be slow. May be removed at a later date.

        Args:
            handler: An external service handler where the image will be relayed.
        """
        interval = 1 / self.config.video.framerate
        while not self._stop_event.is_set():
            frame, timestamp = self.video_stream.read()
            if frame is not None:
                # Image must be converted into file like object to allow sending.
                tmp_file = StringIO()
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                Image.fromarray(img).save(tmp_file, "JPEG")
                self.write_image(handler, tmp_file.getvalue().encode())
                tmp_file.close()
            time.sleep(interval)

    def send_cv_stream(self, handler: Any) -> None:
        """Opens a continuous stream to send Computer Vision processed images.

        Args:
            handler: An external service handler where the image will be relayed.
        """
        interval = 1 / self.config.video.framerate
        quality = self.config.video.quality
        prev_timestamp = 0
        skipped_frames = 0
        max_skippable = self.config.video.framerate * 60
        while not self._stop_event.is_set() and skipped_frames < max_skippable:
            try:
                frame, timestamp = self.video_stream.read()
                if timestamp != prev_timestamp:
                    skipped_frames = 0
                    if frame is not None:
                        ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                        self.write_image(handler, jpeg.tobytes())
                        prev_timestamp = timestamp
                else:
                    skipped_frames += 1
            except cv2.error:
                # Skip frame if an error is encountered.
                pass
            time.sleep(interval)

    def send_pyaudio_stream(self, handler: Any) -> None:
        """Opens a continuous stream to send pyaudio processed sound.

        Args:
            handler: An external service handler where the audio will be relayed.
        """
        handler.wfile.write(base64.decodebytes(self.audio_stream.header))
        last_index = NO_STREAM
        try:
            while not self._stop_event.is_set():
                index, chunk = self.audio_stream.read()
                if chunk and index != NO_STREAM and index != last_index:
                    handler.wfile.write(chunk)
                    last_index = index
        except OSError as error:
            self.log_message(f"send_pyaudio_stream error: {error}", level=logging.ERROR)
