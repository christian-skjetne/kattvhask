# import the necessary packages

# from picamera.array import PiRGBArray
# from picamera import PiCamera
# from imutils.video.pivideostream import PiVideoStream

from pyimagesearch.tempimage import TempImage
import argparse
import warnings
import datetime
import imutils
import imutils.video
import json
import time
import cv2
import numpy as np
import utils


# mask size and pos
mask1x = 30
mask1y = 30
mask2x = 30
mask2y = 150
maskw = maskh = 100
moveMask = False
doDetect = False
doQuit = False


def setMaskSize(masksize):
    global maskh, maskw
    maskw = maskh = masksize


def startDetect(onoff):
    global doDetect
    if onoff == 1:
        doDetect = True
    else:
        doDetect = False


def quit(quit):
    global doQuit
    if quit == 1:
        doQuit = True
    else:
        doDetect = False


def moveMask(event,x,y,flags,param):
    global mask1x, mask1y, mask2x, mask2y, maskh, maskw, moveMask
    if event == cv2.EVENT_LBUTTONDOWN:
        moveMask = True
    elif event == cv2.EVENT_LBUTTONUP:
        moveMask = False
    if moveMask == True:
        if event == cv2.EVENT_MOUSEMOVE:
            if x<mask1x+maskw and x>mask1x and y<mask1y+maskh and y>mask1y:
                mask1x = x-int(maskw/2)
                mask1y = y-int(maskh/2)
            elif x<mask2x+maskw and x>mask2x and y<mask2y+maskh and y>mask2y:
                mask2x = x-int(maskw/2)
                mask2y = y-int(maskh/2)


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True,
    help="path to the JSON configuration file")
args = vars(ap.parse_args())

# filter warnings, load the configuration and initialize the Dropbox
# client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None
resolution = conf.get("resolution", [640, 480])
width = resolution[0]
height = resolution[1]

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])

# Average frame
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

cv2.namedWindow("Security Feed")
cv2.namedWindow("ctrl", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Security Feed", moveMask)
cv2.createTrackbar('1:Exit app', "ctrl", 0, 1, quit)
cv2.createTrackbar('Mask size', "ctrl", maskw, 255, setMaskSize)
cv2.createTrackbar('0:Off\n1:On', "ctrl", 0, 1, startDetect)
cv2.resizeWindow("ctrl", 300, 100)
cv2.moveWindow("ctrl", 500, 35)
cv2.moveWindow("Security Feed", 0, 0)

# TODO: @afel
#   1. Rewrite to use imutils.videostream.VideoStream()
#   2. Track FPS / utilization
#   3. Figure out GUI for creating mask / bounding box
#   4. CircularBuffer to keep X-seconds of video in memory to-be dumped to disk
#   5. Write to a date based folder structure

fps = imutils.video.FPS()

print("Creating videostream")
# Start videostream
is_raspberry_pi = utils.is_raspberry_pi()
vs = imutils.video.VideoStream(usePiCamera=is_raspberry_pi, resolution=resolution)
print(f"Starting videostream.. is_raspberry_pi={is_raspberry_pi}")
vs.start()

# Start timing frames
fps.start()

# capture frames from the camera
while True:
    frame = vs.read()
    if frame is None:
        print("NO frame - re-trying..")
        for i in range(50):
            frame = vs.read()
            if frame is not None:
                break
            time.sleep(0.25)
            print('.', end='', flush=True)
        print("Unable to get a proper reading from videostream..")
        break
    fps.update()
    timestamp = datetime.datetime.now()
    text = "Unoccupied"

    # resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=500)

    if doDetect:
        # Add masks to the image
        mask = np.zeros(frame.shape, np.uint8)
        mask[mask1y:mask1y + maskh, mask1x:mask1x + maskw] = frame[mask1y:mask1y + maskh, mask1x:mask1x + maskw]
        mask[mask2y:mask2y + maskh, mask2x:mask2x + maskw] = frame[mask2y:mask2y + maskh, mask2x:mask2x + maskw]

        gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # if the average frame is None, initialize it
        if avg is None:
            print("[INFO] starting background model...")
            avg = gray.copy().astype("float")
            # rawCapture.truncate(0)
            continue

        # accumulate the weighted average between the current frame and
        # previous frames, then compute the difference between the current
        # frame and running average
        cv2.accumulateWeighted(gray, avg, 0.5)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        _, cnts, hierarchy = cv2.findContours(thresh.copy(),
                                              cv2.RETR_EXTERNAL,
                                              cv2.CHAIN_APPROX_SIMPLE)

        # loop over the contours
        for c in cnts:
            # if the contour is too small, ignore it
            contour_area = cv2.contourArea(c)
            print("Contour area: {}".format(contour_area))
            if contour_area < conf["min_area"]:
                continue

            print("Detected a high contour!")
            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            text = "Occupied"

        # draw the text and timestamp on the frame
        ts = timestamp.strftime("%A %d %B %Y %H:%M:%S")
        cv2.putText(frame,
                    "Room Status: {}".format(text),
                    (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2)
        cv2.putText(frame,
                    ts,
                    (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,
                    (0, 0, 255),
                    1)

        # check to see if the room is occupied
        if text == "Occupied":
            # check to see if enough time has passed between uploads
            if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
                # increment the motion counter
                motionCounter += 1

                # check to see if the number of frames with consistent motion is
                # high enough
                if motionCounter >= conf["min_motion_frames"]:
                    # # check to see if dropbox sohuld be used
                    # if conf["use_dropbox"]:
                    #     # write the image to temporary file
                    #     t = TempImage()
                    #     cv2.imwrite(t.path, frame)
#                     #     # upload the image to Dropbox and cleanup the tempory image
#                     #     print( "[UPLOAD] {}".format(ts))
#                     #     path = "{base_path}/{timestamp}.jpg".format(
#                     #         base_path=conf["dropbox_base_path"], timestamp=ts)
#                     #     client.put_file(path, open(t.path, "rb"))
                    #     t.cleanup()

                    # update the last uploaded timestamp and reset the motion
                    # counter
                    lastUploaded = timestamp
                    motionCounter = 0

        # otherwise, the room is not occupied
        else:
            motionCounter = 0

    if fps._numFrames % 100 == 0:
        fps.stop()
        print("FPS: fps={}, elapsed={}".format(fps.fps(), fps.elapsed()))

    # check to see if the frames should be displayed to screen
    if conf["show_video"]:

        cv2.rectangle(frame, (mask1x, mask1y), (mask1x + maskw, mask1y + maskh), (255, 0, 0), 2)
        cv2.rectangle(frame, (mask2x, mask2y), (mask2x + maskw, mask2y + maskh), (255, 0, 0), 2)

        # display the security feed
        cv2.imshow("Security Feed", frame)

        key = cv2.waitKey(1) & 0xFF

        # if the `q` key is pressed, break from the loop
        if key == ord("q") or doQuit == True:
            vs.stop()
            break
