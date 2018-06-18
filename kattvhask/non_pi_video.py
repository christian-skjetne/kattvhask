# import the necessary packages
from pyimagesearch.tempimage import TempImage
from pyimagesearch.keyclipwriterjoin import KeyClipWriter

# from picamera.array import PiRGBArray
# from picamera import PiCamera
# from imutils.video.pivideostream import PiVideoStream
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2
# import numpy as np
import cronus.beat as beat
import os


doQuit = False


def quit(quit):
    global doQuit
    if quit == 1:
        doQuit = True


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="path to the JSON configuration file")
args = vars(ap.parse_args())

# filter warnings, load the configuration and initialize the Dropbox
# client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None
fps = 28  # conf["fps"]
beat.set_rate(fps)

width = 640  # 320
height = 480  # 240

# initialize the camera and grab a reference to the raw camera capture
# vs = PiVideoStream((width, height), fps, conf["rotation"]).start()
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print( "[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])

# initialize key clip writer and the consecutive number of
# frames that have *not* contained any action
kcw = KeyClipWriter(bufSize=1, timeout=0.01)
consecFrames = 0
recFrames = 0

lastUploaded = datetime.datetime.now()
motionCounter = 0

cv2.namedWindow("Security Feed")
cv2.namedWindow("ctrl", cv2.WINDOW_NORMAL)
cv2.createTrackbar('1:Exit app', "ctrl", 0, 1, quit)
cv2.resizeWindow("ctrl", 300, 100)
cv2.moveWindow("ctrl", 500, 35)
cv2.moveWindow("Security Feed", 1024, 1024)

# capture frames from the camera
lastUploaded = datetime.datetime.now()
while beat.true():
    loopstarttime = datetime.datetime.now()

    ret, frame = cap.read()
    if not ret:
        continue

    timestamp = datetime.datetime.now()
    text = "Unoccupied"

    # resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=500)

    # draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %H:%M:%S")
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
        0.7, (0, 0, 255), 2)


    if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:

        if kcw.recording:
            print("starting stop")
            kcw.finish()
        elif kcw.savedone:
            lastUploaded = timestamp
            current_dir = os.getcwd()
            p = "{}/{}.mkv".format(current_dir,
                datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
            print("startnew")
            kcw.start(p, cv2.VideoWriter_fourcc(*conf["videocodec"]), fps)

    # update the key frame clip buffer
    kcw.update(frame)

    # check to see if the frames should be displayed to screen
    if conf["show_video"]:
        # display the security feed
        cv2.imshow("Security Feed", frame)

        key = cv2.waitKey(1) & 0xFF

        # if the `q` key is pressed, break from the loop
        if key == ord("q") or doQuit == True:
            break

    # clear the stream in preparation for the next frame
    #rawCapture.truncate(0)

    loopT = int((datetime.datetime.now() - loopstarttime).total_seconds() * 1000)

    ##print(int(1000/loopT))
    try:
        beat.sleep()
    except Exception:
        print("beat.sleep(): too much to do, skip sleep")


# if we are in the middle of recording a clip, wrap it up
if kcw.recording:
    kcw.finish()

# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
