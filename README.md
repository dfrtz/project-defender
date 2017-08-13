OpenCV Overview:
http://opencv.org/

How to run:
1. Copy demo data to local folder:
# cp -R .demodata ~/defender

2. Start server with HTTPS and existing user database:
# ./defender.py -s ~/defender/server.pem -u ~/defender/user_auth.db

For some reason HTTP traffic appears to fail loading page, until reason is determined an HTTPS certificate should always be used or API frontend.
