# Defender

Defender is a Python and Javascript based Web Application/Rest API to manage streaming of audio and
video from security cameras, and other devices, in a local network.

Security is currently achieved through a combination of HTTPS certificates, and a salted
User/Password database with PBKDF2 SHA512 combo.

For simplicity and greater compatibility with low end devices, video is streamed as MJPEG, and audio
is streamed as WAV (meaning bandwidth usage is not optimized). Streams can be saved using separate
applications with support for HTTP, such as FFMPEG, VLC, etc.

Currently this application supports Video streaming through OpenCV:  
http://opencv.org/

And audio through PyAudio:  
https://pypi.python.org/pypi/PyAudio


### Requirements

* Python3.6
* System with video and/or audio capture device


### Recommendations

* Raspberry Pi 3 or equivalent hardware
* Webcam with builtin microphone. Tested on Logitech C210.


### Quick Start

1. Setup OpenCV and Python environment with:  
[How to setup Raspberry Pi](SETUP.md)

2. Copy frontend demo data to local folder:
    ```
    cp -R defender/demodata ~/.defender
    cp -R defender/html ~/.defender
    ```

3. Update the configuration file with values to match your environment and devices' capabilities:
    ```
    defender/scripts/defend.py --list-devices
    v4l2-ctl --list-devices
    vi ~/.defender/config.json
    ```

4. Generate new custom HTTPS certificate:
    ```
    openssl req -newkey rsa:4096 -nodes -keyout ~/.defender/key.pem -x509 -days 365 -out ~/.defender/server.pem
    ```

5. If setup for 'virtualenv' per Step 1, ensure you are working on that project:
    ```
    workon opencv
    ```

6. Start server with:
    ```
    defender/scripts/defend.py -c ~/.defender/config.json
    ```

7. Add a user and password to the database:
    ```
    # Skip add to use default:default
    user add <new user name>
    
    # If new user was added, remove default:
    user remove default
    ```

8. Attempt to load the video stream in a browser by going to:
    ```
    https://<hostname or ip>:<port>/video
    ```


#### Known Limitations

* For some reason HTTP traffic appears to fail loading page/serving API calls, until reason is
determined HTTPS should always be used. Well, HTTPS should always be used anyways.
* Multiple concurrent connections to audio streams may overflow buffer and degrade playback.
* Password hashing can leading to slowdown with the initial load of the provided HTML frontend
unless the JS scripts are minified into one.


### What does the future hold?

* Multiple streams per device.
* Motion tracking.
* Audio Playback (two way communication).
* Support for controlling remote motorized devices, such as turret cameras, drones, etc.
* Builtin A/V recording through application, instead of with 3rd party applications (FFMPEG/VLC).
* Possibly additional compression formats for A/V streams.
* Migrate HTTP interfaces to Flask.
* Implement API sessions to increase authorization speed on lower end devices.
