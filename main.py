#!/usr/bin/env python3

import sys
import asyncio
import signal
from tkinter import *
import time
import itertools
from collections import deque
from threading import Thread
import functools
import random
import json
import pendulum
from typing import Dict

import numpy as np
import cv2
from PIL import Image, ImageTk
import imutils
from web_server import get_server
import web_server


class Kattvhask:

    def __init__(self, loop, config : Dict=None, headless=False):
        self.root = None
        self.capture = None
        self.rect = None
        self.image = None
        self.rectangles = []
        self.active_rect = None
        self.moving = False
        self.prev_curX = None
        self.prev_curY = None
        self.rect_border_width = 5.0

        # For motion detection algorithm
        self.frame_queue = deque(maxlen=3)
        self.image_acc = None
        self.motion_detected = False
        self.good_contours_count = 0
        self.loop = loop

        self.config = config
        self.headless = headless


        if not self.headless:
            print("Running in UI mode")
            self.create_gui()

        self.parse_config()
        self.init_video_stream()

    def parse_config(self):
        if not self.config:
            return

        for rect in self.config.get("rectangles", []):
            x0 = rect.get("x0")
            y0 = rect.get("y0")
            x1 = rect.get("x1")
            y1 = rect.get("y1")

            if not self.headless:
                # Create tk rectangles
                new_rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline='green', width=self.rect_border_width, tags="rectangle")
                self.canvas.itemconfig(new_rect, outline='red')
                self.rectangles.append(new_rect)
            else:
                # Create 'dummy' rectangles
                self.rectangles.append({
                    "bbox": (x0, y0, x1, y1)
                })

    def create_gui(self):
        self.root = Tk()
        self.canvas = Canvas(self.root, width=500, height=300, bd=10, bg='white')
        self.canvas.focus_set()
        self.canvas.pack(expand=YES, fill=BOTH)
        self.canvas.bind("<ButtonPress-3>", self.on_right_button_press)
        # self.canvas.bind("<ButtonPress-3>", self.right_click)
        self.canvas.bind("<ButtonPress-1>", self.on_button_single_press)
        self.canvas.bind("<Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Key>", self.on_key)
        self.canvas.grid(row=0, column=0, columnspan=2)

        b = Button(width=10, height=1, text='Quit', command=self.quit)
        b.grid(row=1, column=0)
        b2 = Button(width=10, height=1, text='Clear', command=self.clear)
        b2.grid(row=1, column=1)
        btn_save = Button(width=10, height=1, text='Save', command=self.save)
        btn_save.grid(row=2, column=0)

        # self.popup = Menu(self.root, tearoff=0)
        # self.popup.add_command(label="Remove")

    # def right_click(self, event):
    #     try:
    #         self.popup.tk_popup(event.x_root, event.y_root, 0)
    #     finally:
    #         self.popup.grab_release()
    def save(self):
        """Save all rectangles to a config file (json)."""
        with open('config.json', 'w') as cfg_file:
            print("Save setup")
            data = {'rectangles': []}
            for rect in self.rectangles:
                bbox = self.canvas.bbox(rect)
                x0, y0, x1, y1 = bbox
                data["rectangles"].append({
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1
                })
            # Write dictionary to cfg_file (json serialized)
            json.dump(data, cfg_file)

    def clear(self):
        self.active_rect = None
        for item in self.rectangles:
            self.canvas.delete(item)
        self.rectangles = []

    def get_bbox(self, item):
        if not self.headless:
            return self.canvas.bbox(item)
        return item.get("bbox")

    def point_inside_bbox(self, curX, curY, bbox):
        x0, y0, x1, y1 = bbox
        if curX >= x0 and curX <= x1:
            if curY >= y0 and curY <= y1:
                return True
        return False

    def get_rectangle_at_point(self, curX, curY):
        for item in self.rectangles:
                bbox = self.canvas.bbox(item)
                # print("bbox: {}".format(bbox))
                if self.point_inside_bbox(curX, curY, bbox):
                    return item
        return None

    def cursor_at_rectangle_border(self, curX, curY, rectangle):
        """Returns true if the click was nearby the rectangle's border, else false"""
        bbox = self.canvas.bbox(rectangle)
        x0, y0, x1, y1 = bbox
        item_width = int(self.rect_border_width) + 2

        min_x_boundary = range(x0 - item_width, x0 + item_width)
        max_x_boundary = range(x1 - item_width, x1 + item_width)
        min_y_boundary = range(y0 - item_width, y0 + item_width)
        max_y_boundary = range(y1 - item_width, y1 + item_width)

        def is_inside_x_axis(y):
            return y >= x0 - item_width and y <= x1 + item_width

        def is_inside_y_axis(x):
            return x >= y0 - item_width and x <= y1 + item_width

        if is_inside_y_axis(curY) and curY in itertools.chain(min_y_boundary, max_y_boundary):
            return True

        if is_inside_x_axis(curX) and curX in itertools.chain(min_x_boundary, max_x_boundary):
            return True

        return False

    def on_right_button_press(self, event):
        curX = self.canvas.canvasx(event.x)
        curY = self.canvas.canvasy(event.y)

        rectangle_under_cursor = self.get_rectangle_at_point(curX, curY)
        if not rectangle_under_cursor:
            return

        # remove from canvas and internal refs
        self.rectangles.remove(rectangle_under_cursor)
        self.canvas.delete(rectangle_under_cursor)

    def on_button_single_press(self, event):
        curX = self.canvas.canvasx(event.x)
        curY = self.canvas.canvasy(event.y)
        print("on_button_single_click: canvasxy({}, {}), event.xy=({}, {})".format(curX, curY, event.x, event.y))

        # rectangle_under_cursor = self.get_rectangle_at_point(curX, curY)
        # all_rects = self.canvas.find_withtag("rectangle")

        rectangle_under_cursor = self.get_rectangle_at_point(curX, curY)
        if not rectangle_under_cursor:
            # No rectangle under cursor
            rect = self.canvas.create_rectangle(curX, curY, curX, curY, outline='green', width=self.rect_border_width, tags="rectangle")
            self.rectangles.append(rect)
            self.active_rect = rect
        else:
            if self.active_rect:
                self.canvas.itemconfig(self.active_rect, outline='red')
            self.active_rect = rectangle_under_cursor
            self.canvas.itemconfig(self.active_rect, outline='green')
            click_rect_border = self.cursor_at_rectangle_border(curX, curY, rectangle_under_cursor)
            if click_rect_border:
                print("Border was clicked")
                self.moving = True

        self.prev_curX = curX
        self.prev_curY = curY

    def on_button_release(self, event):
        if self.active_rect:
            self.canvas.itemconfig(self.active_rect, outline='red')
            self.active_rect = None
            self.moving = False
            self.prev_curX = None
            self.prev_curY = None

    def on_move_press(self, event):
        curX = self.canvas.canvasx(event.x)
        curY = self.canvas.canvasy(event.y)

        if self.active_rect:
            rect = self.active_rect

            coords = self.canvas.coords(rect)
            x0, y0, x1, y1 = coords

            # print("on_move_press: coords for rectangle: {}".format(coords))
            # print("on_move_press: bbox: {}, currentXY=({}, {}), prev_XY=({}, {}), event.xy=({}, {})"
            #     .format(bbox, curX, curY, self.prev_curX, self.prev_curY, event.x, event.y))

            diff_x = curX - self.prev_curX
            diff_y = curY - self.prev_curY

            if self.moving:
                # Move instead of resize
                self.canvas.move(self.active_rect, diff_x, diff_y)
            else:
                # Resize
                diff_x = abs(diff_x)
                diff_y = abs(diff_x)
                if curX < self.prev_curX:
                    # decrease
                    x0 -= diff_x
                    x1 += diff_x
                else:
                    # increase
                    x0 += diff_x
                    x1 -= diff_x

                if curY < self.prev_curY:
                    # decrease
                    y0 -= diff_y
                    y1 += diff_y
                else:
                    # increase
                    y0 += diff_y
                    y1 -= diff_y

                # Update item coordinates
                self.canvas.coords(rect, x0, y0, x1, y1)
            self.prev_curX, self.prev_curY = curX, curY

    def on_key(self, event):
        if event.char == 'q':
            self.quit()

    def callback(self, event):
        print("callback")
        widget = event.widget
        widget.focus_set()

    def quit(self):
        if not self.headless:
            self.root.destroy()
        self.capture.release()

    def init_video_stream(self):
        self.capture = cv2.VideoCapture(0)
        # Warmup time
        time.sleep(1)

    def do_detect2(self, frame):
        if len(self.frame_queue) < 3:
            return False

        if len(self.rectangles) == 0:
            return False

        if self.moving or self.active_rect:
            return False

        _, _, curr = self.frame_queue

        # Create mask to the image
        mask = np.zeros(curr.shape, np.uint8)

        # Copy relevant portions of frame into mask
        for roi in self.rectangles:
            bbox = self.get_bbox(roi)

            x1, y1, x2, y2 = bbox
            mask[y1:y2, x1:x2] = curr[y1:y2, x1:x2]

        cv2.accumulateWeighted(mask, self.image_acc, 0.5)
        delta = cv2.absdiff(mask, cv2.convertScaleAbs(self.image_acc))

        delta_thresh = 5
        thresh = cv2.threshold(delta, delta_thresh, 266, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        c_mask, contours, hierachy = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = 1500
        found_contours_in_frame = 0
        for c in contours:
            # Find contours of greater size than some pre-defined area.
            # We only want motion detection for reasonally sized movements
            contour_area = cv2.contourArea(c)
            if contour_area < min_area:
                continue

            self.motion_detected = True
            self.good_contours_count += 1
            found_contours_in_frame += 1

            if self.good_contours_count > 5:
                x, y, w, h = cv2.boundingRect(c)
                print(f"Detected: {x}, {y} {w} {h}")
                cv2.rectangle(frame, (x, y), (x + w, y + w), (0, 255, 0), 2)

                # trigger new websocket message
                self.notify_motion()

        if found_contours_in_frame == 0 and self.motion_detected:
            print(f"No movement... Good contours: {self.good_contours_count}")
            self.motion_detected = False
            self.good_contours_count = 0

    def notify_motion(self):
        # Got new motion alert
        async def send_alert():
            ts = pendulum.now()
            await web_server.queue.put(f"{ts}: Motion detected!")

        asyncio.run_coroutine_threadsafe(send_alert(), loop=self.loop)

    def run(self):
        try:
            while True:
                grabbed, frame = self.capture.read()
                if not grabbed:
                    if not self.capture.isOpened():
                        break
                    else:
                        continue

                gray_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                gray_and_blurred = cv2.GaussianBlur(gray_frame, (21, 21), 0)

                # initialize accumulation
                if self.image_acc is None:
                    self.image_acc = gray_and_blurred.copy().astype("float")
                    # self.image_acc = np.empty(np.shape(frame))

                # print("first frame shape: {}".format(frame.shape))
                # print("image_acc shape: {}".format(self.image_acc.shape))


                # Update frame queue
                self.frame_queue.append(gray_and_blurred)

                self.do_detect2(frame)

                if not self.headless:
                    img = Image.fromarray(frame)
                    b, g, r = img.split()
                    img = Image.merge("RGB", (r, g, b))
                    photo = ImageTk.PhotoImage(image=img)
                    if not self.image:
                        self.image = self.canvas.create_image(0, 0, image=photo, anchor=NW, tags="photo")
                    else:
                        self.canvas.itemconfig(self.image, image=photo)
                    self.root.update()

                # if cv2.waitKey(10) == 27:
                #     break

            if not self.headless:
                self.root.mainloop()
        except KeyboardInterrupt as err:
            print("User ctrl+c'ed us.. Time to quit!")
            self.quit()
            raise err

if __name__ == "__main__":
    if not imutils.is_cv3():
        print("Kattvhask needs OpenCV 3.X.")
        sys.exit(1)

    print("Start websocket server..")
    new_loop = asyncio.new_event_loop()

    def start_loop(loop):
        asyncio.set_event_loop(loop)

        print("Start asyncio in threaded loop..")
        loop.run_forever()

    def shutdown_task():
        print("Shutdown loop")
        loop = asyncio.get_event_loop()
        all_tasks = asyncio.Task.all_tasks(loop=loop)
        asyncio.gather(loop=loop, *all_tasks, return_exceptions=True).cancel()

    print("Creating and starting backgrund thread..")
    t = Thread(target=web_server.start_server, args=(new_loop,))
    t.start()

    try:
        print("Start GUI..")
        cfg = None
        headless = False
        if len(sys.argv) > 1:
            if '-c' in sys.argv[1:]:
                print("Reading config file.")
                with open('config.json', 'r') as f:
                    cfg = json.load(f)

            if '-q' in sys.argv[1:]:
                print("Headless mode")
                headless = True


        app = Kattvhask(new_loop, config=cfg, headless=headless)
        app.run()
    except KeyboardInterrupt:
        print("GUI quited..")
        new_loop.call_soon_threadsafe(shutdown_task)
        new_loop.stop()

    # Ensure that async thread is done
    t.join()
