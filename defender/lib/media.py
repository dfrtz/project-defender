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

import cv2
import pyaudio

from PIL import Image


class LogService(object):
    """Base service class which allows logging to a file and output.

    Attribute:
        logger: A logging object to write messages out to storage.
    """

    def __init__(self, logger):
        self.logger = logger

    def log_message(self, message, external=False, level=logging.INFO):
        """Logs a message to storage and to output visible to users.

        Args:
            message: A string representing the message to save and display.
            external: A boolean to determine if the message is visible to user.
            level: A logging.level used to determine the severity of the message.
        """
        if self.logger:
            self.logger.log(level, message)
        if external:
            print(message)


class VideoConfig(object):
    """Configuration information to control video streams.

    Attributes:
        device: An integer representing the device index of the video input to open.
        width: An integer for the width of the images captures in pixels.
        height: An integer for the height of the images captures in pixels.
        framerate: An integer amount of the maximum amount of images to capture per second.
        quality: An integer representing the image quality after compression between 0-100
    """
    DEVICE = 0
    WIDTH = 640
    HEIGHT = 480
    FRAMERATE = 30
    QUALITY = 85

    def __init__(self, config=None):
        """Initializes attributes from a user specified configuration object or defaults.

        Args:
            config: Dictionary containing user predefined values for initialization."""
        if not config:
            config = {}
        self.device = config.get('device', VideoConfig.DEVICE)
        self.width = config.get('width', VideoConfig.WIDTH)
        self.height = config.get('height', VideoConfig.HEIGHT)
        self.framerate = config.get('fps', VideoConfig.FRAMERATE)
        self.quality = config.get('quality', VideoConfig.QUALITY)


class VideoStream(LogService):
    """Streaming service to pull data from a video input device and serve to multiple requesters.

    Attributes:
        config: A VideoConfig containing information for the stream.
        _image: A bytes like object representing the most recently captured image.
        _stop_event: A threading.Event() used to control start and stop operations on the capture thread.
    """

    def __init__(self, config, logger=None):
        super(VideoStream, self).__init__(logger)
        self.config = config
        self._image = None
        self._stop_event = threading.Event()
        self._stop_event.set()

    def start(self):
        """Creates the background capture thread to read images from the input asynchronously.

        Returns:
            Self for chaining calls.
        """
        if self._stop_event.is_set():
            self._stop_event.clear()
            self.log_message('Video stream starting.', True)
            threading.Thread(target=self.process_stream, args=()).start()
        else:
            self.log_message('Video stream cannot start, already capturing.', True)
        return self

    def process_stream(self, heartbeat_interval=1):
        """Initializes video stream for continuous access until service is stopped.

        Args:
            heartbeat_interval: An integer representing how often to check for an open device in seconds.
        """
        while not self._stop_event.is_set():
            stream = cv2.VideoCapture(self.config.device)
            stream.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            if stream.isOpened():
                break
            self.log_message('Video stream could not open, waiting {} seconds and trying again'
                             .format(heartbeat_interval), True)
            time.sleep(heartbeat_interval)

        self.log_message('Video stream running.', True)
        while stream.isOpened() and not self._stop_event.is_set():
            captured, image = stream.read()
            if captured:
                self._image = image
        stream.release()
        self._image = None
        self.log_message('Video stream stopped.', True)

    def read(self):
        """Provides the most recently captured image.

        Returns:
            A bytes like object representing the most recently captured image, or None if no image is available.
        """
        return self._image

    def stop(self):
        """Signals the background capture thread to stop reading images."""
        if not self._stop_event.is_set():
            self.log_message('Video stream stopping.', True)
            self._stop_event.set()
        else:
            self.log_message('Video stream offline. Aborting repeat shutdown.', True)


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

    def __init__(self, config=None):
        """Initializes attributes from a user specified configuration object or defaults.

        Args:
            config: Dictionary containing user predefined values for initialization."""
        if not config:
            config = {}
        self.device = config.get('device', AudioConfig.DEVICE)
        self.chunk = config.get('chunk', AudioConfig.CHUNK)
        self.format = AudioConfig.FORMAT
        self.channels = config.get('channels', AudioConfig.CHANNELS)
        self.framerate = config.get('rate', AudioConfig.RATE)


class AudioStream(LogService):
    """Streaming service to pull data from an audio input device and serve to multiple requesters.

    Attributes:
        config: An Audio containing information for the stream.
        _chunk: A bytes like object representing the most recently captured audio.
        _chunk_index: An integer tracking the offset of the recent audio chunk to signal data has changed.
        _stream: A blocking audio stream which will be stopped on shutdown.
        _stop_event: A threading.Event() used to control start and stop operations on the capture thread.
        header: A base64 encoded byte string representing the beginning of an audio file.
    """

    # Error handler taken from: alsa-lib.git include/error.h
    # typedef void (*snd_lib_error_handler_t)(const char *file, int line, const char *function, int err, const char *fmt)
    ERR_HANDLER = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
    NO_STREAM = -1

    def __init__(self, config, logger=None):
        super(AudioStream, self).__init__(logger)
        self.config = config
        self._chunk = None
        self._chunk_index = AudioStream.NO_STREAM
        self._stream = None
        self._stop_event = threading.Event()
        self._stop_event.set()
        self.header = ''

    def start(self):
        """Creates the background capture thread to listen for audio from the input asynchronously.

        Returns:
            Self for chaining calls.
        """
        if self._stop_event.is_set():
            self._stop_event.clear()
            self.log_message('Audio stream starting.', True)
            threading.Thread(target=self.process_stream, args=()).start()
        else:
            self.log_message('Audio stream cannot start, already capturing.', True)
        return self

    def process_stream(self, heartbeat_interval=1):
        """Initializes audio stream for continuous access until service is stopped.

        Args:
            heartbeat_interval: An integer representing how often to check for an open device in seconds.
        """
        self.header = AudioStream.mk_wav_header(self.config.channels, self.config.format, self.config.framerate)
        chunk_size = self.config.chunk
        try:
            # Find the correct device ID
            dev_id = 0
            device_found = False
            while not self._stop_event.is_set():
                with AudioStream.hide_c_errors('libasound.so'):
                    audio = pyaudio.PyAudio()
                for i in range(audio.get_device_count()):
                    dev = audio.get_device_info_by_index(i)
                    if isinstance(self.config.device, int):
                        if self.config.device == dev['index']:
                            device_found = True
                            break
                    # Indexes are not reliable, allow a name string to be used instead
                    if isinstance(self.config.device, str):
                        if self.config.device in dev['name']:
                            dev_id = dev['index']
                            device_found = True
                            break
                if device_found:
                    break
                audio.terminate()
                self.log_message('Audio stream could not open missing device, waiting {} seconds and trying again'
                                 .format(heartbeat_interval), True)
                time.sleep(heartbeat_interval)

            # Open the stream only if a device ID was found
            self._stream = audio.open(format=self.config.format,
                                      channels=self.config.channels,
                                      rate=self.config.framerate,
                                      input=True,
                                      input_device_index=dev_id,
                                      frames_per_buffer=chunk_size)

            self.log_message('Audio stream running.', True)
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
                print('Audio Service low level error: {}'.format(error))
                self.log_message('AudioStream:process_stream - low level error - {}'.format(error), level=logging.ERROR)

            self._chunk = None
            self._chunk_index = AudioStream.NO_STREAM
            self._stream.stop_stream()
            self._stream.close()
            audio.terminate()
            self.log_message('Audio stream stopped.', True)
        except OSError as error:
            self.log_message('AudioStream:process_stream - high level - error {}'.format(error), level=logging.ERROR)

    def read(self):
        """Provides the most recently captured audio chunk data.

        Returns:
            A tuple with index of audio stream to determine if data is new, and bytes like object representing the most
            recently captured audio chunk, or (-1, None) if no audio is available.
        """
        return self._chunk_index, self._chunk

    def stop(self):
        """Signals the background capture thread to stop listening for audio."""
        if not self._stop_event.is_set():
            self.log_message('Audio stream stopping.', True)
            self._stop_event.set()
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
        else:
            self.log_message('Audio stream offline. Aborting repeat shutdown.', True)

    @staticmethod
    def gen_lock_id():
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(16))

    @staticmethod
    def mk_wav_header(channels, audio_format, framerate):
        """Creates header information for a WAV file.

        Args:
            channels: An integer representing the desired number of input channels to capture.
            audio_format: An integer representing the format of of the audio stream.
            framerate: An integer representing the desired rate (in Hz)
        """
        with BytesIO() as memory_file, wave.open(memory_file, 'w') as wave_file:
            wave_file.setnchannels(channels)
            wave_file.setsampwidth(pyaudio.get_sample_size(audio_format))
            wave_file.setframerate(framerate)
            wave_file.writeframes(b'')
            encoding = base64.encodebytes(memory_file.getvalue())
        return encoding

    @staticmethod
    def _c_error_handler(file, line, function_name, err, fmt):
        """Handles an error message from C based libraries."""
        # Error handler reference taken from: alsa-lib.git include/error.h
        # typedef void (*snd_lib_error_handler_t)(const char *file, int line, const char *function, int err, const char *fmt)
        pass

    @staticmethod
    @contextmanager
    def hide_c_errors(lib_file):
        """Sets a temporary error handler for a C based library.

        Args:
            lib_file: A string representing a library file name. Example: 'libasound.so'
        """
        lib = ctypes.cdll.LoadLibrary(lib_file)
        lib.snd_lib_error_set_handler(AudioStream.ERR_HANDLER(AudioStream._c_error_handler))
        yield
        lib.snd_lib_error_set_handler(None)


class MediaConfig(object):
    """Configuration information to control a group of audio and video streams.

    Attributes:
        video: A VideoConfig containing information for video input devices.
        audio: An AudioConfig containing information for audio input devices.
        log: A string path to storage where logging messages will be stored.
        debug: A boolean representing whether the service is in debugging mode.
    """

    def __init__(self, config=None):
        """Initializes attributes from a user specified configuration object or defaults.

        Args:
            config: Dictionary containing user predefined values for initialization."""
        if not config:
            config = {}
        self.video = VideoConfig(config.get('video', None))
        self.audio = AudioConfig(config.get('audio', None))
        self.log = os.path.abspath(os.path.expanduser(config.get('log', 'media.log')))
        self.debug = False


class MediaService(LogService):
    """Service to control flow of multiple audio and video streams, and relay captured data to a external handlers.

    Attributes:
        config: A MediaConfig containing information for audio and video streams.
        video_stream: A VideoStream service pulling data from a video input device.
        audio_stream: An AudioStream service pulling data from a audio input device.
        hog: A CV HOGDescriptor (histogram of oriented gradients) used to perform image post processing.
        _stop_event: A threading.Event() used to control start and stop operations on the services.
    """

    def __init__(self, config):
        super(MediaService, self).__init__(logging.getLogger(__name__))
        self.config = config
        self.video_stream = None
        self.audio_stream = None
        self.hog = cv2.HOGDescriptor()
        self._stop_event = threading.Event()
        self._stop_event.set()
        self.setup_logger(config.log)

    def setup_logger(self, log):
        """Creates a logger to record the lifecycle of the server.

        Returns:
            A logger instance with custom formatting for the server.
        """
        if not len(self.logger.handlers):
            formatter = logging.Formatter(fmt='{asctime} - {levelname} - {message}', datefmt='%Y-%m-%dT%H:%M:%S.%s',
                                          style='{')
            file_handler = logging.handlers.RotatingFileHandler(log, maxBytes=10000000, backupCount=5, encoding='UTF-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)

    def set_debug(self, enabled=False):
        """Enables or disables debug output from the server.

        This method is disruptive while the setting is being applied.

        Args:
            enabled: A boolean representing whether debug mode should be enabled.
        """
        self.shutdown()
        if enabled:
            self.log_message('Media service enabling debugging', True)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.log_message('Media service disabling debugging', True)
            self.logger.setLevel(logging.INFO)
        self.start()

    def start(self):
        """Creates the audio and video server threads to service new handler requests."""
        if self._stop_event.is_set():
            self._stop_event.clear()
            self.log_message('Media service starting', True)
            self.video_stream = VideoStream(self.config.video, self.logger).start()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self.audio_stream = AudioStream(self.config.audio, self.logger).start()
            self.log_message('Media service listening to video and audio.')
        else:
            self.log_message('Media service cannot start, streams already running.', True)

    def shutdown(self):
        """Stops the audio and video server threads and prevents serving new handler requests."""
        if not self._stop_event.is_set():
            self._stop_event.set()
            self.log_message('Media service shutting down', True)
            self.video_stream.stop()
            self.audio_stream.stop()
            self.log_message('Media service offline', True)
        else:
            self.log_message('Media service offline. Aborting repeat shutdown.', True)

    @staticmethod
    def list_devices():
        print('Audio Devices:')
        with AudioStream.hide_c_errors('libasound.so'):
            p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            for key, value in dev.items():
                print('{:<25} {}'.format(key + ':', value))
            print()
        p.terminate()
        print()

    @staticmethod
    def write_image(handler, image):
        """Writes a single image to an external handler.

        Args:
            handler: An external service handler where the image will be relayed.
            image: A bytes like object representing an image.
        """
        handler.wfile.write(b'--jpgbound\r\n')
        handler.send_header('X-Timestamp', time.time())
        handler.send_header('Content-Length', len(image))
        handler.send_header('Content-Type', 'image/jpeg')
        handler.end_headers()
        handler.wfile.write(image)

    def send_cv_stream(self, handler):
        """Opens a continuous stream to send Computer Vision processed images.

        Args:
            handler: An external service handler where the image will be relayed.
        """
        interval = 1 / self.config.video.framerate
        quality = self.config.video.quality
        while not self._stop_event.is_set():
            try:
                frame = self.video_stream.read()
                if frame is not None:
                    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                    self.write_image(handler, jpeg.tobytes())
            except cv2.error:
                pass
            time.sleep(interval)

    def send_cv_detection_stream(self, handler):
        """Opens a continuous stream to send Computer Vision processed images with various object detection models.

        Args:
            handler: An external service handler where the image will be relayed.
        """
        interval = 1 / self.config.video.framerate
        quality = self.config.video.quality
        while not self._stop_event.is_set():
            frame = self.video_stream.read()
            if frame is not None:
                rects, weights = self.hog.detectMultiScale(frame, winStride=(4, 4), padding=(8, 8), scale=1.05)
                for (x, y, w, h) in rects:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                encoded, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                if encoded:
                    self.write_image(handler, jpeg.tobytes())
            time.sleep(interval)

    def send_cv_pil_stream(self, handler):
        """Opens a continuous stream to send Computer Vision processed images using Python Imaging Library (PIL).

        Current testing has shown this method of processing to be slow. May be removed at a later date.

        Args:
            handler: An external service handler where the image will be relayed.
        """
        interval = 1 / self.config.video.framerate
        while not self._stop_event.is_set():
            frame = self.video_stream.read()
            if frame is not None:
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                tmp_file = StringIO()
                Image.fromarray(img).save(tmp_file, 'JPEG')
                self.write_image(handler, tmp_file.getvalue())
                tmp_file.close()
            time.sleep(interval)

    def send_pyaudio_stream(self, handler):
        """Opens a continuous stream to send Computer Vision processed images.

        Args:
            handler: An external service handler where the image will be relayed.
        """
        handler.wfile.write(base64.decodebytes(self.audio_stream.header))
        last_index = AudioStream.NO_STREAM
        try:
            while not self._stop_event.is_set():
                index, chunk = self.audio_stream.read()
                if chunk and index != AudioStream.NO_STREAM and index != last_index:
                    handler.wfile.write(chunk)
                    last_index = index
        except OSError as error:
            self.log_message('MediaService:send_pyaudio_stream error: {}'.format(error), level=logging.ERROR)
