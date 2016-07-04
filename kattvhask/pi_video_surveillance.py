# import the necessary packages
from pyimagesearch.tempimage import TempImage
from pyimagesearch.keyclipwriter import KeyClipWriter
from dropbox.client import DropboxOAuth2FlowNoRedirect
from dropbox.client import DropboxClient
from picamera.array import PiRGBArray
from picamera import PiCamera
from imutils.video.pivideostream import PiVideoStream
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2
import numpy as np
import cronus.beat as beat

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

#mask size and pos
mask1x = conf["mask1x"]
mask1y = conf["mask1y"]
mask2x = conf["mask2x"]
mask2y = conf["mask2y"]
maskw = maskh = conf["masksize"]
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
		beat.set_rate(conf["fps"])
	else:
		doDetect = False
		beat.set_rate(50)
		
		
def quit(quit):
	global doQuit
	if quit == 1:
		doQuit = True
	else:
		doDetect = False

def moveMask(event,x,y,flags,param):
	global mask1x, mask1y, mask2x, mask2y, maskh, maskw, moveMask
	if doDetect:
		return
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





# check to see if the Dropbox should be used
if conf["use_dropbox"]:
	# connect to dropbox and start the session authorization process
	flow = DropboxOAuth2FlowNoRedirect(conf["dropbox_key"], conf["dropbox_secret"])
	print( "[INFO] Authorize this application: {}".format(flow.start()))
	authCode = input("Enter auth code here: ").strip()

	# finish the authorization and grab the Dropbox client
	(accessToken, userID) = flow.finish(authCode)
	client = DropboxClient(accessToken)
	print( "[SUCCESS] dropbox account linked")

# initialize the camera 
vs = PiVideoStream(conf["resolution"], conf["fps"], conf["rotation"]).start()

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print( "[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])

# initialize key clip writer and the consecutive number of
# frames that have *not* contained any action
kcw = KeyClipWriter(bufSize=conf["videobuffer"], timeout=0.01)
consecFrames = 0
recFrames = 0

avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

cv2.namedWindow("Security Feed")
cv2.namedWindow("ctrl", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Security Feed",moveMask)
cv2.createTrackbar('1:Exit app',"ctrl",0,1,quit)
cv2.createTrackbar('Mask size',"ctrl",maskw,255,setMaskSize)
cv2.createTrackbar('0:Off\n1:On',"ctrl",0,1,startDetect)
cv2.resizeWindow("ctrl", 300, 100)
cv2.moveWindow("ctrl",500,35)
cv2.moveWindow("Security Feed",0,0)

beat.set_rate(50)

loopT = 1
while beat.true():
	loopstarttime = datetime.datetime.now()
	# grab the raw NumPy array representing the image and initialize
	# the timestamp and occupied/unoccupied text
	#frame = f.array
	frame = vs.read()
	timestamp = datetime.datetime.now()
	text = "Unoccupied"

	# resize the frame, convert it to grayscale, and blur it
	frame = imutils.resize(frame, width=500)
	#START OF DETECT
	if doDetect:
	
		#Add masks to the image
		mask = np.zeros(frame.shape,np.uint8)
		mask[mask1y:mask1y+maskh,mask1x:mask1x+maskw] = frame[mask1y:mask1y+maskh,mask1x:mask1x+maskw]
		mask[mask2y:mask2y+maskh,mask2x:mask2x+maskw] = frame[mask2y:mask2y+maskh,mask2x:mask2x+maskw]
	
		gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
		gray = cv2.GaussianBlur(gray, (21, 21), 0)

		# if the average frame is None, initialize it
		if avg is None:
			print( "[INFO] starting background model...")
			avg = gray.copy().astype("float")
			#rawCapture.truncate(0)
			continue

		# accumulate the weighted average between the current frame and
		# previous frames, then compute the difference between the current
		# frame and running average
		cv2.accumulateWeighted(gray, avg, 0.5)
		frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

		
		
		# threshold the delta image, dilate the thresholded image to fill
		# in holes, then find contours on thresholded image
		thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255,
			cv2.THRESH_BINARY)[1]
		thresh = cv2.dilate(thresh, None, iterations=2)
		#(cnts, _)
		_,cnts,hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
			cv2.CHAIN_APPROX_SIMPLE)

		# loop over the contours
		for c in cnts:
			# if the contour is too small, ignore it
			if cv2.contourArea(c) < conf["min_area"]:
				continue

			# compute the bounding box for the contour, draw it on the frame,
			# and update the text
			(x, y, w, h) = cv2.boundingRect(c)
			cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
			text = "Occupied"

		# draw the text and timestamp on the frame
		ts = timestamp.strftime("%A %d %B %Y %H:%M:%S")
		#cv2.putText(frame, "   Status: {}".format(text), (10, 20),
		#	cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
			0.7, (0, 0, 255), 2)

		# check to see if the room is occupied
		if text == "Occupied":
			
			####PHOTO####
##			
##			# check to see if enough time has passed between uploads
##			if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
##				# increment the motion counter
##				motionCounter += 1
##
##				# check to see if the number of frames with consistent motion is
##				# high enough
##				if motionCounter >= conf["min_motion_frames"]:
##					# check to see if dropbox should be used
##					if conf["use_dropbox"]:
##						# write the image to temporary file
##						t = TempImage()
##						cv2.imwrite(t.path, frame)
##
##						# upload the image to Dropbox and cleanup the tempory image
##						print( "[UPLOAD] {}".format(ts))
##						path = "{base_path}/{timestamp}.jpg".format(
##							base_path=conf["dropbox_base_path"], timestamp=ts)
##						client.put_file(path, open(t.path, "rb"))
##						t.cleanup()
##					elif conf["save_photo"]:
##						cv2.imwrite("{base_path}/{timestamp}.jpg".format(
##							base_path=conf["outdir"], timestamp=ts), frame)
##					# update the last uploaded timestamp and reset the motion
##					# counter
##					lastUploaded = timestamp
##					motionCounter = 0

			####VIDEO####
			if kcw.recording:
				consecFrames = 0
			else:
				consecFrames += 1
			
			if consecFrames >= conf["min_motion_frames"]:
				# if we are not already recording, start recording
				if not kcw.recording:
					timestamp = datetime.datetime.now()
					p = "{}/{}.mkv".format(conf["outdir"],
						timestamp.strftime("%Y%m%d-%H%M%S"))
					kcw.start(p, cv2.VideoWriter_fourcc(*conf["videocodec"]),
						conf["fps"])
			
			
		# otherwise, the room is not occupied
		else:
			motionCounter = 0
			if kcw.recording:
				consecFrames += 1
			else:
				consecFrames = 0
			
			
	#END OF DETECT
	if kcw.recording:
		recFrames = conf["videobuffer"]-consecFrames
		##recFrames = 1000/loopT
		cv2.putText(frame, "* {}".format(int(recFrames)), (10, 40),
					cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
					
				
	
	# update the key frame clip buffer
	kcw.update(frame)
	
	# if we are recording and reached a threshold on consecutive
	# number of frames with no action, stop recording the clip TODO: use == or >=.. what is best?
	if kcw.recording and consecFrames >= conf["videobuffer"]:
		kcw.finish()
		consecFrames = 0

	# check to see if the frames should be displayed to screen
	if conf["show_video"]:
	
		cv2.rectangle(frame, (mask1x, mask1y), (mask1x + maskw, mask1y + maskh), (255, 0, 0), 2)
		cv2.rectangle(frame, (mask2x, mask2y), (mask2x + maskw, mask2y + maskh), (255, 0, 0), 2)
	
		# display the security feed
		cv2.imshow("Security Feed", frame)
		
		key = cv2.waitKey(1) & 0xFF

		# if the `q` key is pressed, break from the loop
		if key == ord("q") or doQuit == True:
			break
	
	#print(int(1000/int((datetime.datetime.now() - loopstarttime).total_seconds()*1000)))
	
	try:
		beat.sleep()
	except:
		pass#print("skip sleep fps:{}".format(int(1000/int((datetime.datetime.now() - loopstarttime).total_seconds()*1000))))

# if we are in the middle of recording a clip, wrap it up
if kcw.recording:
	kcw.finish()
	
# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
	
	
	
