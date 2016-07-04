# kattvhask
Kontroll av trafikktelling ved hjelp av sensorkamera


HVORDAN INSTALLERE OPENCV på RasPi3:
fra: http://www.pyimagesearch.com/2016/04/18/install-guide-raspberry-pi-3-raspbian-jessie-opencv-3/

# fjern wolfram alpha for å spare plass:
<code>$ sudo apt-get purge wolfram-engine</code>

# oppdater OS:
<code>$ sudo apt-get update</code>
<code>$ sudo apt-get upgrade</code>

# CMake:
<code>$ sudo apt-get install build-essential cmake pkg-config</code>

<code>$ sudo apt-get install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev</code>

<code>$ sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev</code>
<code>$ sudo apt-get install libxvidcore-dev libx264-dev</code>

<code>$ sudo apt-get install libgtk2.0-dev</code>

<code>$ sudo apt-get install libatlas-base-dev gfortran</code>

<code>$ sudo apt-get install python2.7-dev python3-dev</code>

<code>$ cd ~</code>
<code>$ wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.1.0.zip</code>
<code>$ unzip opencv.zip</code>

<code>$ wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.1.0.zip</code>
<code>$ unzip opencv_contrib.zip</code>

<code>$ wget https://bootstrap.pypa.io/get-pip.py</code>
<code>$ sudo python get-pip.py</code>

<code>$ wget https://bootstrap.pypa.io/get-pip.py</code>
<code>$ sudo python get-pip.py</code>

<code>$ echo -e "\n# virtualenv and virtualenvwrapper" >> ~/.profile</code>
<code>$ echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.profile</code>
<code>$ echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.profile</code>

<code>$ source ~/.profile</code>

<code>$ mkvirtualenv cv -p python3</code>

# RUN THIS TO SELECT THE VIRTUAL ENVIRONMENT:
<code>$ source ~/.profile</code>
<code>$ workon cv</code>

<code>$ pip install numpy</code>

<code>$ workon cv</code>

<code>$ cd ~/opencv-3.1.0/</code>
<code>$ mkdir build</code>
<code>$ cd build</code>
<code>$ cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D INSTALL_PYTHON_EXAMPLES=ON \
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib-3.1.0/modules \
    -D BUILD_EXAMPLES=ON ..</code>

<code>$ make -j4</code>

<code>$ make clean</code>
<code>$ make</code>

<code>$ sudo make install</code>
<code>$ sudo ldconfig</code>

Finish installing OpenCV on your Pi

<code>$ cd /usr/local/lib/python3.4/site-packages/</code>
<code>$ sudo mv cv2.cpython-34m.so cv2.so</code>

<code>$ cd ~/.virtualenvs/cv/lib/python3.4/site-packages/</code>
<code>$ ln -s /usr/local/lib/python3.4/site-packages/cv2.so cv2.so</code>

# TEST THE INSTALL:
<code>$ source ~/.profile </code>
<code>$ workon cv</code>
<code>$ python</code>
<code>>>> import cv2
>>> cv2.__version__
'3.1.0'
>>></code>

# REMOVE FILES:
<code>$ rm -rf opencv-3.1.0 opencv_contrib-3.1.0</code>




