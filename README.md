# kattvhask
Kontroll av trafikktelling ved hjelp av sensorkamera


HVORDAN INSTALLERE OPENCV på RasPi3:
fra: http://www.pyimagesearch.com/2016/04/18/install-guide-raspberry-pi-3-raspbian-jessie-opencv-3/

# fjern wolfram alpha for å spare plass:
$ sudo apt-get purge wolfram-engine

# oppdater OS:
$ sudo apt-get update
$ sudo apt-get upgrade

# CMake:
$ sudo apt-get install build-essential cmake pkg-config

$ sudo apt-get install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev

$ sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
$ sudo apt-get install libxvidcore-dev libx264-dev

$ sudo apt-get install libgtk2.0-dev

$ sudo apt-get install libatlas-base-dev gfortran

$ sudo apt-get install python2.7-dev python3-dev

$ cd ~
$ wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.1.0.zip
$ unzip opencv.zip

$ wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.1.0.zip
$ unzip opencv_contrib.zip

$ wget https://bootstrap.pypa.io/get-pip.py
$ sudo python get-pip.py

$ wget https://bootstrap.pypa.io/get-pip.py
$ sudo python get-pip.py

$ echo -e "\n# virtualenv and virtualenvwrapper" >> ~/.profile
$ echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.profile
$ echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.profile

$ source ~/.profile

$ mkvirtualenv cv -p python3

# RUN THIS TO SELECT THE VIRTUAL ENVIRONMENT:
$ source ~/.profile
$ workon cv

$ pip install numpy

$ workon cv

$ cd ~/opencv-3.1.0/
$ mkdir build
$ cd build
$ cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D INSTALL_PYTHON_EXAMPLES=ON \
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib-3.1.0/modules \
    -D BUILD_EXAMPLES=ON ..

$ make -j4

$ make clean
$ make

$ sudo make install
$ sudo ldconfig

Finish installing OpenCV on your Pi

$ cd /usr/local/lib/python3.4/site-packages/
$ sudo mv cv2.cpython-34m.so cv2.so

$ cd ~/.virtualenvs/cv/lib/python3.4/site-packages/
$ ln -s /usr/local/lib/python3.4/site-packages/cv2.so cv2.so

# TEST THE INSTALL:
$ source ~/.profile 
$ workon cv
$ python
>>> import cv2
>>> cv2.__version__
'3.1.0'
>>>

# REMOVE FILES:
$ rm -rf opencv-3.1.0 opencv_contrib-3.1.0




