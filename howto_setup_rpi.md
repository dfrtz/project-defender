#READ THIS NOTICE
This guide was written and tested on Raspbian Stretch Lite (2017-08-16) and OpenCV 3.3.0, however the same
steps (should) work in any Debian based environment with minimal to no modification. Other Linux distros will
require medium to heavy modification of the commands such as installing dependencies. Your mileage may vary.
##### Note: Improper use of 'dd' can overwrite any partition on your system. Do not proceed with any commands without absolute certainty they are targeting the correct partition.


# Sections:
##### I. Download Raspberry Pi Debian (Raspbian) Image
##### II. Installing the Operating System
##### III. Prepare Operating System for Headless First Boot
##### IV. Prepare Operating System for Standard User Access
##### V. Setup Python Development Environment
##### VI. Setup OpenCV Development Environment
##### VII. Setup Defender Development Environment

### I. Download Raspberry Pi Debian (Raspbian) Image

Find and download an image from Raspbian Official:
https://www.raspberrypi.org/downloads/


### II. Installing the Operating System

##### Note: Improper use of 'dd' can overwrite any partition on your system. Do not proceed with any commands without absolute certainty they are targeting the correct partition.

1. List the current devices and their mount points:  
`lsblk`

2. Insert the SD card into the SD card slot, or an external adapter.

3. Check for the new device and location (/dev/sdX):  
`lsblk`

4. If the device was mounted automatically, unmount it from the system:  
`umount /dev/sdX`

5. Copy the image to the SD card using 'dd':  
`dd if=2017-08-16-raspbian-stretch.img of=/dev/sdX conv=fsync status=progress`


### III. Prepare Operating System for Headless First Boot

1. Make two new directories to mount the SD card boot and system partitions:  
`mkdir -vp /mnt/rpi/boot /mnt/rpi/system`

2. List the devices to find the boot and system partitions on the SD card. The SD card device should be split into two
pieces after installing the OS from "Section I", similar to /dev/sdb1 and /dev/sdb2  
`lsblk`

2. Mount the boot partition. This should be the smaller of the 2 partitions found in Step 2:  
`mount /dev/sdXx /mnt/rpi/boot`

3. Add an 'ssh' file to the boot directory. This will enable SSH on first boot of the Raspberry Pi to allow login and
configuration. The file will be deleted after first boot.  
`touch /mnt/rpi/boot/ssh`

4. Unmount boot partition:  
`umount /mnt/rpi/boot`

5. Mount the system partition. This should be the larger of the two partitions found in step 2:  
`mount /dev/sdXx /mnt/rpi/system`

6. If using wired connection, skip and go to step 9. If using wireless, edit the network configuration to allow Wifi to
connect on boot. Open the interface configuration file using a text editor. Examples:  
`vi /mnt/rpi/system/etc/network/interfaces`  
OR:  
`nano /mnt/rpi/system/etc/network/interfaces`

7. Add everything after <Begin> and before <End> tags, replacing wpa-ssid and wpa-psk as appropriate for your network:
    ```
    <Begin>
    auto lo
    iface lo inet loopback
    
    auto eth0
    iface eth0 inet dhcp
    
    allow-hotplug wlan0
    auto wlan0
    iface wlan0 inet dhcp
            wpa-ssid "My network name"
            wpa-psk "My network password"
    <End>
    ```

8. Save file and exit text editor. Examples:  
If using vi: `ESC > Shift + : > wq > Enter`  
If using nano: `CTRL + X > Enter`  

9. Unmount system partition:  
`umount /mnt/rpi/system`

10. Ensure device is completely unmounted, and remove from SD card slot or external adapter:  
`lsblk`


### IV. Prepare Operating System for Standard User Access

1. Install SD card into Raspberry Pi.

2. Power on device.

3. If using DHCP, you will need to find the IP address of the Raspberry Pi. Examples:  
`arp -a`  
`ping -c1 raspberrypi`

4. SSH into the Raspberry Pi as user 'pi' and password 'raspberry' via hostname (if reachable) or IP:  
`ssh pi@raspberrypi`  
OR:  
`ssh pi@<IP address>`

5. Change 'pi' passwd to remove popup about default password on future logins:  
`passwd`

6. Switch to root user from user 'pi':  
`sudo -i`

7. Enter configuration tool and update hostname of device on network and enable SSH:  
`sudo raspi-config`
   - Navigation Breadcrumbs:
    ```
    Main Menu > Hostname
    Main Menu > Interfacing Options > SSH
    ```

8. Exit configuration tool by selecting "Finish". Do not reboot yet.

9. Create a new administrator user:  
`adduser <username>`

10. Add the new user to sudo and media groups:  
`adduser <username> sudo`  
`adduser <username> video`  
`adduser <username> audio`

11. Logout of root and Raspberry Pi, and reconnect as new user:  
`exit`  
`exit`  
`ssh <username>@<IP address>`

12. Delete 'pi' user:  
`sudo deluser pi`

13. Change 'root' password to secure system:  
`sudo passwd root`

14. Update packages:  
`sudo apt-get update`  
`sudo apt-get upgrade`

15. Reboot:  
`sudo reboot`


### V. Setup Python Development Environment

1. Install 'pip' Python Package Manager and Development Library:  
`sudo apt-get install python3-pip python3-dev`

2. Install virtual environment:  
`sudo pip3 install virtualenv virtualenvwrapper`  
`sudo rm -rf ~/.cache/pip`

3. Update user profile with virtual environment wrapper for additional commands and to show currently active workspace:  
`echo "export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3" >> ~/.profile`  
`echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.profile`  
`echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.profile`  


### VI. Setup OpenCV Development Environment

1. Make development folder and virtual environment for OpenCV:  
`mkdir opencv`  
`cd opencv`  
`mkvirtualenv opencv -p python3`  
`workon opencv`

2. Install NumPy:  
`pip install numpy`

3. Download the latest source code:  
`wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.3.0.zip`  
`unzip opencv.zip`  
`wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.3.0.zip`  
`unzip opencv_contrib.zip`  

4. Install required packages for compiling OpenCV with image and video extensions.  
    - For compiling:  
    `sudo apt-get install build-essential cmake pkg-config`  
    - For image manipulation:  
    `sudo apt-get install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev`  
    - For video manipulation:  
    `sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev`  
    - For mathematical optimizations:  
    `sudo apt-get install libatlas-base-dev gfortran`

5. Compile OpenCV:  
    `cd opencv-3.3.0/`  
    `mkdir build`  
    `cd build`  
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
    `make -j4`

    - If any errors are encountered and you need to start over, clean and make:  
    `make clean`  
    `make -j4`

    - Additional Note - If not running Raspbian outlined in this guide, you may need to add the following to the 'cmake'
command to build correctly:  
    `-D ENABLE_PRECOMPILED_HEADERS=OFF \`

    - Additional Note x2 - If you encounter log spam due to camera returning "extraneous bytes before marker" messages but the
stream has no issues (for example, with Logitech C270 cameras), you may wish to comment out the following line
from opencv-3.3.0/3rdparty/libjpeg/jdmarker.c and rebuild:  
    `//WARNMS2(cinfo, JWRN_EXTRANEOUS_DATA, cinfo->marker->discarded_bytes, c);`

6. Install OpenCV:  
`sudo make install`  
`sudo ldconfig`

7. Symlink library to virtual environment (original .so name and Python subdirectory will vary based on versions):
`ln -s /usr/local/lib/python3.x/site-packages/cv2.cpython-35m.so ~/.virtualenvs/opencv/lib/python3.x/site-packages/cv2.so`

8. Verify installation and link to virtual environment:
    ```
    python
    >>> import cv2
    >>> cv2.__version__
    '3.3.0'
    >>> quit()
    ```
9. Optional - Cleanup OpenCV build environment:  
`cd ../../..`  
`rm -r opencv`


### VII. Setup Defender Development Environment

1. Install OS dependencies:  
`sudo apt-get install portaudio19-dev`

2. Install Python dependencies:  
`pip install pyaudio`  
`pip install imutils`

3. Install system dependencies
    - For displaying video devices:  
    `sudo apt-get install v4l-utils`