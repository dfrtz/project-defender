import base64
import logging
import logging.handlers
import threading
import time
import wave
from io import StringIO
import random
import string

import cv2
import pyaudio
from PIL import Image


class VideoStream(object):
    def __init__(self, source=0):
        self.source = source
        self.grabbed = None
        self.frame = None
        self._stop_event = threading.Event()

    def start(self):
        print('Video stream starting.')
        threading.Thread(target=self.update, args=()).start()
        return self

    def update(self):
        self._stop_event.clear()

        stream = cv2.VideoCapture(self.source)
        # stream.set(cv2.CAP_PROP_FRAME_WIDTH, 320);
        # stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 240);

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
    CHUNK = 128
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100

    HEADER_WAV = b'UklGRiQAAABXQVZFZm10IBAAAAABAAIARKwAABCxAgAEABAAZGF0YQAAAAA='  # WAV, 2 Channel, 44100 Hz

    def __init__(self):
        self.grabbed = None
        self.chunk = None
        self._stop_event = threading.Event()

        self.audio_handlers = {}

    def start(self):
        print('Audio stream starting.')
        # threading.Thread(target=self.update, args=()).start()
        return self

    def update(self):
        self._stop_event.clear()

        p = pyaudio.PyAudio()

        stream = p.open(format=AudioStream.FORMAT,
                        channels=AudioStream.CHANNELS,
                        rate=AudioStream.RATE,
                        input=True,
                        frames_per_buffer=AudioStream.CHUNK)

        print('Audio stream running.')
        try:
            while not self._stop_event.is_set():
                for key, event in self.audio_handlers.items():
                    event.clear()
                self.chunk = stream.read(AudioStream.CHUNK)
                for key, event in self.audio_handlers.items():
                    event.set()
        except KeyboardInterrupt as e:
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

    def gen_lock_id(self):
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(16))

    def mk_wav_header(self, cached=True):
        if cached:
            with open('headeronly.wav', 'wb') as file_out:
                file_out.write(base64.decodebytes(AudioStream.HEADER_WAV))
        else:
            p = pyaudio.PyAudio()
            wf = wave.open('headeronly.wav', 'wb')
            wf.setnchannels(AudioStream.CHANNELS)
            wf.setsampwidth(p.get_sample_size(AudioStream.FORMAT))
            wf.setframerate(AudioStream.RATE)
            wf.writeframes(b'')
            wf.close()
            p.terminate()


class MediaConfig(object):
    def __init__(self):
        self.camera_dev = 0
        self.log = 'media.log'
        self.debug = False


class MediaService(object):
    TEMPLATE = b'''
    <html>
        <head></head>
        <body>
            <img src="video"/>
            <video controls="" autoplay="" name="media">
                <source src="audio" type="audio/x-wav">
            </video>
        </body>
    </html>'''

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
        if self._thread is None:
            self.log_message('Media service starting', True)
            self.video_stream = VideoStream(source=self.config.camera_dev).start()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self.audio_stream = AudioStream().start()
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

    def write_image(self, handler, image):
        handler.wfile.write(b'--jpgbound\r\n')
        handler.send_header('X-Timestamp', time.time())
        handler.send_header('Content-Length', len(image))
        handler.send_header('Content-Type', 'image/jpeg')
        handler.end_headers()
        handler.wfile.write(image)

    def send_cv_stream(self, handler):
        while True:
            try:
                frame = self.video_stream.read()
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])

                self.write_image(handler, jpeg.tobytes())

                time.sleep(0.03)
            except KeyboardInterrupt:
                break

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
                tmp_file = StringIO.StringIO()
                Image.fromarray(img).save(tmp_file, 'JPEG')

                self.write_image(handler, tmp_file.getvalue())
                tmp_file.close()

                time.sleep(0.05)
            except KeyboardInterrupt:
                break

    def send_audio_stream(self, handler):
        handler.wfile.write(base64.decodebytes(AudioStream.HEADER_WAV))
        lock = threading.Event()
        lock_id = self.audio_stream.gen_lock_id()
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
        CHANNELS = 2
        RATE = 44100

        p = pyaudio.PyAudio()

        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        print("* recording")

        handler.wfile.write(base64.decodebytes(AudioStream.HEADER_WAV))
        try:
            while True:
                data = stream.read(CHUNK)
                if len(data):
                    handler.wfile.write(data)
        except KeyboardInterrupt as e:
            pass

        print("* stopping")
        stream.stop_stream()
        stream.close()
        p.terminate()
