# kattvhask

## Description

Detect motion in a predefined area in the video stream. When such an event occurs
then capture and store the video stream while the motion is in place.

Also stores metadata for each events to easier search / query the output.


## Requirements

- Raspberry Pi 3 or Linux laptop
- Raspbian / Ubuntu / Debian
- OpenCV 3.3, ffmpeg, ffprobe


## Build OpenCV 3.3

We wanted the most optimized OpenCV for our raspberry pi, so we followed the brilliant tutorial of https://www.pyimagesearch.com/2017/10/09/optimizing-opencv-on-the-raspberry-pi/ where we optimize it for the raspberry pi.

- Download opencv-3.3 and extract somewhere
- Download opencv_contrib-3.3 and extract somewhere


```
$ cd opencv-3.3.0
$ mkdir build && cd build
$ cmake -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=/usr/local -D OPENCV_EXTRA_MODULES_PATH=/home/pi/opencv_contrib-3.3.0/modules -D ENABLE_NEON=ON -D ENABLE_VFPV3=ON -D BUILD_TESTS=OFF -D INSTALL_PYTHON_EXAMPLES=ON -D BUILD_EXAMPLES=ON ..
```

## Run?

python main.py --help
> print 'help' here


# Resources

- https://www.pyimagesearch.com/2016/02/29/saving-key-event-video-clips-with-opencv/
- https://www.pyimagesearch.com/2017/10/09/optimizing-opencv-on-the-raspberry-pi/
