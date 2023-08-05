# Defender

[![opencv](https://img.shields.io/badge/-OpenCV-%23white.svg?logo=opencv&logoColor=white)](https://opencv.org/)
[![raspberry-pi](https://img.shields.io/badge/-Raspberry_Pi-C51A4A?logo=Raspberry-Pi&logoColor=white)](https://www.raspberrypi.com/)
[![os: linux](https://img.shields.io/badge/os-linux-blue)](https://docs.python.org/3.6/)
[![python: 3.6+](https://img.shields.io/badge/python-3.6_|_3.7-blue)](https://devguide.python.org/versions)
[![python style: google](https://img.shields.io/badge/python%20style-google-blue)](https://google.github.io/styleguide/pyguide.html)
[![imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://github.com/PyCQA/isort)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![code style: pycodestyle](https://img.shields.io/badge/code%20style-pycodestyle-green)](https://github.com/PyCQA/pycodestyle)
[![doc style: pydocstyle](https://img.shields.io/badge/doc%20style-pydocstyle-green)](https://github.com/PyCQA/pydocstyle)
[![static typing: mypy](https://img.shields.io/badge/static_typing-mypy-green)](https://github.com/python/mypy)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)
[![testing: pytest](https://img.shields.io/badge/testing-pytest-yellowgreen)](https://github.com/pytest-dev/pytest)
[![security: bandit](https://img.shields.io/badge/security-bandit-black)](https://github.com/PyCQA/bandit)
[![license: Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-lightgrey)](LICENSE)
![maintenance: inactive](https://img.shields.io/badge/Maintenance%20Status-Inactive-yellowgreen.svg)


> **Note**: This project is no longer actively maintained. No support is provided for bugfixes, security updates, etc.
It was originally started as a hobby, and built around Python versions 3.4-3.6, and original Angular. It has many
examples for processing images, video, audio, HTTP requests, web apps, etc., although likely out of date. The project
also contains a good baseline for code quality standards on new projects, so it remains available for referencing.

Defender is a Python and Javascript based Web Application/Rest API to manage streaming of audio and
video from security cameras, and other devices, in a local network.

Security is currently achieved through a combination of HTTPS certificates, and a salted
User/Password database with PBKDF2 SHA512 combo.

For simplicity and greater compatibility with low-end devices, video is streamed as MJPEG, and audio
is streamed as WAV (meaning bandwidth usage is not optimized). Streams can be saved using separate
applications with support for HTTP, such as FFMPEG, VLC, etc.

This application supports Video streaming through OpenCV:  
http://opencv.org/

And audio through PyAudio:  
https://pypi.python.org/pypi/PyAudio


### Requirements

* Python3.6+
* System with video and/or audio capture device


### Recommendations

* Raspberry Pi 3 or equivalent hardware
* Webcam with builtin microphone. Tested on Logitech C210.


### Quick Start

1. Setup OpenCV and Python environment with:  
[How to set up Raspberry Pi](SETUP.md)

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
determined HTTPS should always be used. Well, HTTPS should always be used.
* Multiple concurrent connections to audio streams may overflow buffer and degrade playback.
* Password hashing can lead to slowdown with the initial load of the provided HTML frontend
unless the JS scripts are minified into one.


### What does the future hold?

> **Note**: This project is no longer actively maintained. No support is provided for bugfixes, security updates, etc.
It was originally started as a hobby, and built around Python versions 3.4-3.6, and original Angular. It has many
examples for processing images, video, audio, HTTP requests, web apps, etc., although likely out of date. The project
also contains a good baseline for code quality standards on new projects, so it remains available for referencing.

* Multiple streams per device.
* Motion tracking.
* Audio Playback (two way communication).
* Support for controlling remote motorized devices, such as nerf turret cameras, drones, etc.
* Builtin A/V recording through application, instead of with 3rd party applications (FFMPEG/VLC).
* Possibly additional compression formats for A/V streams.
* Migrate HTTP interfaces to Flask/FastAPI.
* Implement API sessions to increase authorization speed on lower end devices.
