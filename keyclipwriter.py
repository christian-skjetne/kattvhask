# import the necessary packages
from collections import deque
from threading import Thread
from queue import Queue
import time
import cv2
import os
import pendulum


class KeyClipWriter:
    def __init__(self, base_outputdir, bufSize=64, timeout=0.01):
        # store the maximum buffer size of frames to be kept
        # in memory along with the sleep timeout during threading
        self.bufSize = bufSize
        self.timeout = timeout

        # initialize the buffer of frames, queue of frames that
        # need to be written to file, video writer, writer thread,
        # and boolean indicating whether recording has started or not
        self.frames = deque(maxlen=bufSize)
        self.Q = None
        self.writer = None
        self.thread = None
        self.recording = False
        self._time_start_record = None
        self.base_outputdir = base_outputdir
        if not os.path.isdir(self.base_outputdir):
            os.mkdir(self.base_outputdir)
        self._today = pendulum.today().date()
        self.path = os.path.join(self.base_outputdir, str(self._today))

        self.mkpath()

    def update(self, frame):
        # update the frames buffer
        self.frames.appendleft(frame)

        # if we are recording, update the queue as well
        if self.recording:
            self.Q.put(frame)

    def mkpath(self):
        if not os.path.isdir(self.path):
            os.mkdir(self.path)
            return True
        return False

    def start(self, fourcc, fps):
        # indicate that we are recording, start the video writer,
        # and initialize the queue of frames that need to be written
        # to the video file
        self.recording = True

        # Group messages based on the current date
        self._time_start_record = pendulum.now()
        now_date = self.start_time.date()
        if self._today < now_date:
            # New date - need to create a new folder
            self._today = now_date
            self.path = os.path.join(self.base_outputdir, str(self._today))
            self.mkpath()

        filename = ".".join([self.start_time.strftime("%H:%m:%S"), "mkv"])
        output_file = os.path.join(self.path, filename)

        self.writer = cv2.VideoWriter(output_file, fourcc, fps,
            (self.frames[0].shape[1], self.frames[0].shape[0]), True)
        self.Q = Queue()

        # loop over the frames in the deque structure and add them
        # to the queue
        for i in range(len(self.frames), 0, -1):
            self.Q.put(self.frames[i - 1])

        # start a thread write frames to the video file
        self.thread = Thread(target=self.write, args=())
        self.thread.daemon = True
        self.thread.start()

    def write(self):
        # keep looping
        while self.recording:
            # if we are done recording, exit the thread
            #if not self.recording:
            #   return

            # check to see if there are entries in the queue
            if not self.Q.empty():
                # grab the next frame in the queue and write it
                # to the video file
                frame = self.Q.get()
                self.writer.write(frame)

            # otherwise, the queue is empty, so sleep for a bit
            # so we don't waste CPU cycles
            else:
                time.sleep(self.timeout)

        self.flush()
        self.writer.release()

    def flush(self):
        # empty the queue by flushing all remaining frames to file
        while not self.Q.empty():
            frame = self.Q.get()
            self.writer.write(frame)

    @property
    def start_time(self):
        return self._time_start_record

    @property
    def record_time(self):
        return self._time_stop_record - self._time_start_record

    def finish(self):
        # indicate that we are done recording, join the thread,
        # flush all remaining frames in the queue to file, and
        # release the writer pointer
        self._time_stop_record = pendulum.now()
        print("Done recording. {} seconds".format(self.record_time))
        self.recording = False
        self.thread.join()
        self.flush()
        self.writer.release()
