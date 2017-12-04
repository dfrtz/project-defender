import base64
import logging
import logging.handlers
import random
import string
import threading
import time
import wave
from io import BytesIO
from io import StringIO

import cv2
import pyaudio
from PIL import Image


class VideoStream(object):
    def __init__(self, config):
        self.config = config
        self.grabbed = None
        self.frame = None
        self._stop_event = threading.Event()

    def start(self):
        print('Video stream starting.')
        threading.Thread(target=self.update, args=()).start()
        return self

    def update(self, heartbeat_interval=1):
        self._stop_event.clear()

        stream = cv2.VideoCapture(self.config.device)
        # stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        # stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)

        while not stream.isOpened() and not self._stop_event.is_set():
            print('Video stream could not open, waiting {} seconds and trying again'.format(heartbeat_interval))
            time.sleep(heartbeat_interval)
            stream = cv2.VideoCapture(self.config.device)

        print('Video stream running.')

        while stream.isOpened() and not self._stop_event.is_set():
            self.grabbed, self.frame = stream.read()
        stream.release()
        print('Video stream stopped.')

    def read(self):
        return self.frame

    def stop(self):
        print('Video stream stopping.')
        self._stop_event.set()


class AudioStream(object):
    def __init__(self, config):
        self.config = config
        self.grabbed = None
        self.chunk = None
        self._stop_event = threading.Event()
        self.audio_handlers = {}
        self.header = ''

    def start(self):
        print('Audio stream starting.')
        self.mk_wav_header(self.config.channels, self.config.format, self.config.framerate)
        # threading.Thread(target=self.update, args=()).start()
        return self

    def update(self):
        self._stop_event.clear()

        p = pyaudio.PyAudio()

        stream = p.open(format=self.config.format,
                        channels=self.config.channels,
                        rate=self.config.framerate,
                        input=True,
                        frames_per_buffer=self.config.chunk)

        print('Audio stream running.')
        try:
            while not self._stop_event.is_set():
                for key, event in self.audio_handlers.items():
                    event.clear()
                self.chunk = stream.read()
                for key, event in self.audio_handlers.items():
                    event.set()
        except KeyboardInterrupt:
            pass
        stream.stop_stream()
        stream.close()
        p.terminate()
        print('Audio stream stopped.')

    def read(self):
        return self.chunk

    def stop(self):
        print('Audio stream stopping.')
        self._stop_event.set()

    @staticmethod
    def gen_lock_id():
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(16))

    @staticmethod
    def mk_wav_header(channels, form, framerate):
        memory_file = BytesIO()

        wave_file = wave.open(memory_file, 'w')
        wave_file.setnchannels(channels)
        wave_file.setsampwidth(pyaudio.get_sample_size(form))
        wave_file.setframerate(framerate)
        wave_file.writeframes(b'')
        wave_file.close()

        encoding = base64.encodebytes(memory_file.getvalue())
        memory_file.close()
        return encoding


class VideoConfig(object):
    DEVICE = 0
    WIDTH = 640
    HEIGHT = 480
    FRAMERATE = 30
    QUALITY = 85

    def __init__(self, user_config=None):
        self.device = VideoConfig.DEVICE
        self.width = VideoConfig.WIDTH
        self.height = VideoConfig.HEIGHT
        self.framerate = VideoConfig.FRAMERATE
        self.quality = VideoConfig.QUALITY

        if user_config:
            self.device = user_config.get('device', self.device)
            # TODO validate
            pass


class AudioConfig(object):
    DEVICE = 0
    CHUNK = 128
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100

    def __init__(self, user_config=None):
        self.device = AudioConfig.DEVICE
        self.chunk = AudioConfig.CHUNK
        self.format = AudioConfig.FORMAT
        self.channels = AudioConfig.CHANNELS
        self.framerate = AudioConfig.RATE

        if user_config:
            # TODO validate
            pass


class MediaConfig(object):
    def __init__(self, user_config=None):
        self.video = VideoConfig(user_config.get('video', {}) if user_config else {})
        self.audio = AudioConfig(user_config.get('audio', {}) if user_config else {})

        self.log = 'media.log'
        self.debug = False


class MediaService(object):
    def __init__(self, config):
        self.config = config
        self._thread = None

        self.video_stream = None
        self.audio_stream = None
        self.hog = cv2.HOGDescriptor()

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
            self.log_message('Media service enabling debugging', True)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.log_message('Media service disabling debugging', True)
            self.logger.setLevel(logging.INFO)
        self.start()

    def start(self):
        # TODO debug remove
        # p = pyaudio.PyAudio()
        # for i in range(p.get_device_count()):
        #     dev = p.get_device_info_by_index(i)
        #     print('Slot {} : {} : {}\n'.format(i, dev['name'], dev))

        if self._thread is None:
            self.log_message('Media service starting', True)
            self.video_stream = VideoStream(self.config.video).start()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self.audio_stream = AudioStream(self.config.audio).start()
            self._thread = True
            self.log_message('Media service listening to video and audio.')
        else:
            self.log_message('Media service cannot start, already listening', True)

    def shutdown(self):
        if self._thread is not None:
            self.log_message('Media service shutting down', True)
            self.video_stream.stop()
            self.audio_stream.stop()
            self._thread = None
            self.log_message('Media service offline', True)
        else:
            self.log_message('Media service offline. Aborting repeat shutdown.', True)

    @staticmethod
    def write_image(handler, image):
        handler.wfile.write(b'--jpgbound\r\n')
        handler.send_header('X-Timestamp', time.time())
        handler.send_header('Content-Length', len(image))
        handler.send_header('Content-Type', 'image/jpeg')
        handler.end_headers()
        handler.wfile.write(image)

    def send_cv_stream(self, handler):
        interval = 1 / self.config.video.framerate
        quality = self.config.video.quality
        while True:
            try:
                frame = self.video_stream.read()
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])

                self.write_image(handler, jpeg.tobytes())
            except cv2.error:
                pass
            except KeyboardInterrupt:
                break
            time.sleep(interval)

    def send_cv_detection_stream(self, handler):
        while self.video_stream.isOpened():
            try:
                ret, frame = self.video_stream.read()
                if not ret:
                    continue

                rects, weights = self.hog.detectMultiScale(frame, winStride=(4, 4), padding=(8, 8), scale=1.05)
                for (x, y, w, h) in rects:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                ret, jpeg = cv2.imencode('.jpg', frame)

                self.write_image(handler, jpeg.tobytes())

                time.sleep(0.05)
            except KeyboardInterrupt:
                break

    def send_pil_stream(self, handler):
        while self.video_stream.isOpened():
            try:
                ret, frame = self.video_stream.read()
                if not ret:
                    continue

                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                tmp_file = StringIO()
                Image.fromarray(img).save(tmp_file, 'JPEG')

                self.write_image(handler, tmp_file.getvalue())
                tmp_file.close()

                time.sleep(0.05)
            except KeyboardInterrupt:
                break

    def send_audio_stream(self, handler):
        handler.wfile.write(base64.decodebytes(self.audio_stream.header))
        lock_id = self.audio_stream.gen_lock_id()
        lock = threading.Event()
        self.audio_stream.audio_handlers[lock_id] = lock

        print("Audio lock " + lock_id)
        while True:
            try:
                lock.wait(5000)
                if not lock.is_set():
                    print('audio timeout')
                    break
                chunk = self.audio_stream.read()
                if len(chunk):
                    handler.wfile.write(chunk)
            except KeyboardInterrupt:
                break
        self.audio_stream.audio_handlers.pop(lock_id)

    def send_pyaudio(self, handler):
        CHUNK = 128
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        p = pyaudio.PyAudio()

        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        print("* recording")

        handler.wfile.write(base64.decodebytes(self.audio_stream.header))
        try:
            while True:
                data = stream.read(CHUNK)
                if len(data):
                    handler.wfile.write(data)
        except KeyboardInterrupt:
            pass

        print("* stopping")
        stream.stop_stream()
        stream.close()
        p.terminate()
