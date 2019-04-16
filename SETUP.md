# READ THIS NOTICE

This guide was written and tested on Raspbian Stretch Lite (2018-11-13) and OpenCV 3.3.0, however
the same steps (should) work in any Debian based environment with minimal to no modification. Other
Linux distros will require medium to heavy modification of the commands such as installing
dependencies. Your mileage may vary.

**Note: Improper use of 'dd' can overwrite any partition on your system. Do not proceed with any
commands without absolute certainty they are targeting the correct partition.**


#### Table Of Contents

* [Download Raspbian](#download-raspberry-pi-debian-raspbian-image)
* [Installing OS](#installing-the-operating-system)
* [Prepare OS Headless Boot](#prepare-operating-system-for-headless-boot)
* [Prepare OS For User Access](#prepare-operating-system-for-user-access)
* [Build And Install Python](#build-and-install-python36)
* [Setup Python Dev Environment](#setup-python-development-environment)
* [Setup Defender Dev Environment](#setup-defender-development-environment)
* [Setup OpenCV Dev Environment](#setup-opencv-development-environment)


### Download Raspberry Pi Debian (Raspbian) Image

Find and download an image from Raspbian Official:  
https://www.raspberrypi.org/downloads/


### Installing the Operating System

**Note: Improper use of 'dd' can overwrite any partition on your system. Do not proceed with any
commands without absolute certainty they are targeting the correct partition.**

1. List the current devices and their mount points:
    ```
    lsblk
    ```

2. Insert the SD card into the SD card slot, or an external adapter.

3. Check for the new device and location (/dev/sdX):
    ```
    lsblk
    ```

4. If the device was mounted automatically, unmount it from the system:
    ```
    umount /dev/sdX
    ```

5. Copy the image to the SD card using 'dd':
    ```
    dd if=2018-11-13-raspbian-stretch.img of=/dev/sdX conv=fsync status=progress
    ```


### Prepare Operating System for Headless Boot

1. Make two new directories to mount the SD card boot and system partitions:
    ```
    mkdir -vp /mnt/rpi/boot /mnt/rpi/system
    ```

2. List the devices to find the boot and system partitions on the SD card. The SD card device should
be split into two parts after installing the OS, similar to `/dev/sdb1` and `/dev/sdb2`.
    ```
    lsblk
    ```

3. Mount the boot partition. This should be the smaller of the 2 partitions found in Step 2:
    ```
    mount /dev/sdXx /mnt/rpi/boot
    ```

4. Add an 'ssh' file to the boot directory. This will enable SSH on first boot of the Raspberry Pi
to allow login and configuration. The file will be deleted after first boot.
    ```
    touch /mnt/rpi/boot/ssh
    ```

5. Unmount boot partition:
    ```
    umount /mnt/rpi/boot
    ```

6. Mount the system partition. This should be the larger of the two partitions found in step 2:
    ```
    mount /dev/sdXx /mnt/rpi/system
    ```

7. If using wired connection, skip this step and go to step 9. If using wireless, edit the network
configuration files to allow Wifi to connect on boot.

    * Open the interface configuration file using a text editor. Examples:
    ```
    vi /mnt/rpi/system/etc/network/interfaces
    # OR:
    nano /mnt/rpi/system/etc/network/interfaces
    ```

    * Add everything after <Begin> and before <End> tags, replacing wpa-ssid and wpa-psk as appropriate
    for your network:  
    ```
    ### Begin ###
    auto lo
    iface lo inet loopback
    
    auto eth0
    iface eth0 inet dhcp
    
    allow-hotplug wlan0
    auto wlan0
    iface wlan0 inet dhcp 
        wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf
    ### End ###
    ```

    * Save file and exit text editor. Examples:
    ```
    # If using vi: ESC > Shift + : > wq > Enter
    # If using nano: CTRL + X > Enter
    ```

8. Edit the WPA supplicant file to add one or more network(s).

    * Open the wpa_supplicant configuration file using a text editor. Examples:
    ```
    vi /etc/wpa_supplicant/wpa_supplicant.conf
    # OR:
    nano /etc/wpa_supplicant/wpa_supplicant.conf
    ```

    * Add everything after <Begin> and before <End> tags, replacing wpa-ssid and wpa-psk as
    appropriate for your network:
    ```
    ### Begin ###
    country=US
    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
    update_config=1

    # For a standard network:
    network={
      ssid="My network name"
      psk="My network password"
      scan_ssid=1
    }

    # For a RADIUS network:
    network={
      ssid="My network name"
      key_mgmt=WPA-EAP
      eap=PEAP
      identity="My User Name"
      password="My network password"
      id_str="My network name"
    }
    ### End ###
    ```

    * Save file and exit text editor. Examples:
    ```
    If using vi: ESC > Shift + : > wq > Enter
    If using nano: `CTRL + X > Enter
    ```

9. Unmount system partition:
    ```
    umount /mnt/rpi/system
    ```

10. Ensure device is completely unmounted, and remove from SD card slot or external adapter:
    ```
    lsblk
    ```


### Prepare Operating System for User Access

1. Install SD card into Raspberry Pi.

2. Power on device.

3. If using DHCP, you will need to find the IP address of the Raspberry Pi. Examples:
    ```
    arp -a
    ping -c1 raspberrypi
    ```

4. SSH into the Raspberry Pi as user 'pi' and password 'raspberry' via hostname or IP:
    ```
    ssh pi@raspberrypi
    # OR:
    ssh pi@<IP address>
    ```

5. Change 'pi' passwd to remove popup about default password on future logins:
    ```
    passwd
    ```

6. Switch to root user from user 'pi':
    ```
    sudo -i
    ```

7. Enter configuration tool and update hostname of device on network and enable SSH:
    ```
    sudo raspi-config
    ```
    * Navigation Breadcrumbs:  
    ```
    Main Menu > Network Options > Hostname
    Main Menu > Interfacing Options > SSH
    ```

8. Exit configuration tool by selecting "Finish". Do not reboot yet.

9. Create a new administrator user:
    ```
    adduser <username>
    ```

10. Add the new user to sudo and media groups:
    ```
    adduser <username> sudo
    adduser <username> video
    adduser <username> audio
    ```

11. Logout of root and Raspberry Pi, and reconnect as new user:
    ```
    exit
    exit
    ssh <username>@<IP address>
    ```

12. Delete 'pi' user:
    ```
    sudo deluser pi
    ```

13. Change 'root' password to secure system:
    ```
    sudo passwd root
    ```

14. Update packages:  
    ```
    sudo apt update
    sudo apt upgrade
    ```

15. Reboot:
    ```
    sudo reboot
    ```


### Build and Install Python3.6

1. Install dependencies to build python from source:  
    ```
    sudo apt install build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev \
        libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev
    ```

2. Create directory for source code to compile:
    ```
    mkdir ~/python
    cd ~/python
    ```

3. Pull down the tarball and extract the source:
    ```
    wget https://www.python.org/ftp/python/3.6.8/Python-3.6.8.tar.xz
    tar -xf Python-3.6.8.tar.xz
    ```

4. Configure the source and build:
    ```
    cd Python-3.6.8/
    ./configure
    make -j4
    ```

5. Install:
    ```
    sudo make altinstall
    ```

6. Cleanup source:
    ```
    cd ..
    rm -r Python-3.6.8/
    rm Python-3.6.8.tar.xz
    ```


### Setup Python Development Environment

1. Install 'pip' Python Package Manager and Development Library:
    ```
    sudo apt install python3-pip python3-dev
    ```

2. Install virtual environment:
    ```
    sudo pip3 install virtualenv virtualenvwrapper
    ```

3. Update user profile with virtual environment wrapper for additional commands and to show
currently active workspace:
    ```
    echo "export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3" >> ~/.profile
    echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.profile
    echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.profile
    ```


### Setup Defender Development Environment

1. Create development folder:
    ```
    mkdir -v ~/Development
    ```

2. Clone repo and update location:
    ```
    cd ~/Development
    git clone <remote repo location>
    mv project-defender defender
    ```

3. Make virtual environment for OpenCV:
    ```
    mkvirtualenv opencv -p $(which python3.6)
    workon opencv
    ```

4. Install python project:
    ```
    cd defender
    pip install .
    ```

5. Add git path to virtual OpenCV environment:
    ```
    echo "export PYTHONPATH=~/Development/defender" >> ~/.virtualenvs/opencv/bin/activate
    ```

6. Install OS dependencies:
    ```
    sudo apt install portaudio19-dev
    ```

7. Install system dependencies.
    ```
    # For displaying video devices:
    sudo apt install v4l-utils
    ```


### Setup OpenCV Development Environment

1. Make development folder for OpenCV:
    ```
    mkdir opencv
    cd opencv
    ```

2. Download the latest source code:
    ```
    wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.3.0.zip
    unzip opencv.zip
    wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.3.0.zip
    unzip opencv_contrib.zip
    ```

3. Install required packages for compiling OpenCV with image and video extensions:
    ```
    # For compiling:
    sudo apt install build-essential cmake pkg-config

    # For image manipulation:
    sudo apt install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev

    # For video manipulation:
    sudo apt install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev

    # For mathematical optimizations:
    sudo apt install libatlas-base-dev gfortran
    ```

4. Compile OpenCV:
    ```
    cd opencv-3.3.0/
    mkdir build
    cd build
    ```
    ```
    cmake -D CMAKE_BUILD_TYPE=RELEASE \
        -D CMAKE_INSTALL_PREFIX=/usr/local \
        -D BUILD_EXAMPLES=OFF \
        -D INSTALL_PYTHON_EXAMPLES=OFF \
        -D WITH_FFMPEG=ON \
        -D WITH_JPEG=ON \
        -D BUILD_JPEG=ON \
        -D OPENCV_EXTRA_MODULES_PATH=../../opencv_contrib-3.3.0/modules \
        -D BUILD_EXAMPLES=OFF ..
    ```
    ```
    make -j4
    ```

    > If any errors are encountered and you need to start over, clean, and make:
    ```
    make clean
    make -j4
    ```

    >Additional Note - If not running Raspbian outlined in this guide, you may need to add the
    following to the 'cmake' command to build correctly:
    ```
    -D ENABLE_PRECOMPILED_HEADERS=OFF \
    ```

    > Additional Note x2 - If you encounter log spam due to camera returning "extraneous bytes
    before marker" messages but the stream has no issues (for example, with Logitech C270 cameras),
    you may wish to comment out the following line from opencv-3.3.0/3rdparty/libjpeg/jdmarker.c and
    rebuild:
    ```
    //WARNMS2(cinfo, JWRN_EXTRANEOUS_DATA, cinfo->marker->discarded_bytes, c);
    ```

5. Install OpenCV:
    ```
    sudo make install
    sudo ldconfig
    ```

6. Symlink library to virtual environment (original .so name and Python subdirectory will vary based
on versions):
    ```
    ln -s /usr/local/lib/python3.x/site-packages/cv2.cpython-35m.so ~/.virtualenvs/opencv/lib/python3.x/site-packages/cv2.so
    ```

7. Verify installation and link to virtual environment:
    ```
    python
    >>> import cv2
    >>> cv2.__version__
    '3.3.0'
    >>> quit()
    ```

8. Optional - Cleanup OpenCV build environment:
    ```
    cd ../../..
    rm -r opencv
    ```
