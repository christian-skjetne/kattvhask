#!/usr/bin/env python3

import sys
import asyncio
import signal
import logging
from tkinter import *
import time
import itertools
from collections import deque
import queue
from threading import Thread, Event
import functools
import random
import json
import pendulum
from typing import Dict
import click
import base64
import uuid

import numpy as np
import cv2
from PIL import Image, ImageTk
import imutils
from web_server import get_server
import web_server
from keyclipwriter import KeyClipWriter
import handlers
import logconfig
import utils


LOG = logging.getLogger("kattvhask")
LOG.addHandler(logging.StreamHandler(sys.stdout))
LOG.setLevel(logging.DEBUG)


class Kattvhask:

    def __init__(self, loop, config : Dict=None, headless=False, **kw):
        self.root = None
        self.capture = None
        self.rect = None
        self.image = None
        self.rectangles = []
        self.object_mapping = {}
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
        self.input_changes = queue.Queue()

        self.config = config
        self.headless = headless
        self.kcw = KeyClipWriter("output")
        self.last_notification = None
        self.last_contour_identified = None

        # if "setup_queue" in kw:
        setup_queue = kw.get("setup_queue", None)
        if setup_queue:
            self.setup_queue = setup_queue.sync_q
        else:
            self.setup_queue = None

        self.mqtt = kw.get("mqtt", None)

        if not self.headless:
            LOG.info("Running in UI mode")
            self.create_gui()
        else:
            LOG.info("Running in headless mode")
            if self.config:
                self.parse_config()

        self.init_video_stream()

        # Setup callback for global Observer object
        # web_server.kattvhask_setup.bind_to(self.on_setup_update)

    def parse_config(self):
        if not self.config:
            return

        ws_payload = []
        for rect in self.config.get("rectangles", []):
            rect_id = rect.get("id")
            x0 = rect.get("x0")
            y0 = rect.get("y0")
            x1 = rect.get("x1")
            y1 = rect.get("y1")
            new_rect = {
                "bbox": (x0, y0, x1, y1),
                "id": rect_id
            }
            ws_payload.append(new_rect)

            if not self.headless:
                # Create tk rectangles
                canvas_rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline='green', width=self.rect_border_width, tags="rectangle")
                self.canvas.itemconfig(canvas_rect, outline='red')
                self.rectangles.append(canvas_rect)
                self.object_mapping[canvas_rect] = rect_id
            else:
                # Create 'dummy' rectangles
                self.rectangles.append(new_rect)

        print("kattvhask ws_payload: {}".format(ws_payload))
        # UGLY trick: we wan't to avoid an 'update' event on the
        #           web_server.kattvhask_setup object. Therefore
        #           removing our listener before updating the value.
        #           Then add our 'self.on_setup_update' callback again.
        # web_server.kattvhask_setup.remove_bind(self.on_setup_update)
        # web_server.kattvhask_setup.rectangles = ws_payload
        # web_server.kattvhask_setup.bind_to(self.on_setup_update)
        self.setup_queue.put(ws_payload)

    def add_rectangle(self, uuid, bbox):
        print(f"Add new rectangle...{uuid} {bbox}")

    def update_rectangle(self, uuid, bbox):
        print(f"update_rectangle: {uuid} and {bbox}")
        if not self.headless:
            try:
                item_id = [k for k,v in self.object_mapping.items() if v == uuid][0]
            except IndexError:
                print(f"Unable to find canvas with uuid={uuid}")
                return
            # Update existing rectangle on the canvas
            self.canvas.coords(item_id, *bbox)
            print("  GUI mode rect update")
        else:
            for rect in self.rectangles:
                if rect.get("id") == uuid:
                    # Set new bbox
                    rect["bbox"] = bbox
                    print("  headless update rect")

    def on_setup_update(self, in_rects):
        """Receive updated setup information from the user (websocket) about
        reactangles, positions and sizes.

        Must compare with the ones we already have and update accordingly.
        """

        try:
            incoming_object = self.setup_queue.get_nowait()
            print("Incoming setup object update: {}".format(incoming_object))
            self.input_changes(incoming_object)
        except janus.Empty:
            print("on_setup_update: No setup object update yet..")
            return None

        # print("on_setup_update: New update, rectangles is now: {}".format(in_rects))
        # self.input_changes.put(in_rects)

    def on_input_change(self, in_rects):
        print("on_input_change")
        if not self.headless:
            my_rectangle_uuids = list(self.object_mapping.values())
        else:
            my_rectangle_uuids = list(x.get('id') for x in self.rectangles)

        for in_rect in in_rects:
            if "bbox" in in_rect:
                bbox = in_rect.get("bbox")
            else:
                bbox = (in_rect['x0'], in_rect['y0'], in_rect['x1'], in_rect['y1'])
                bbox = tuple(map(lambda x: int(x), bbox))

            if in_rect.get("uuid") in my_rectangle_uuids:
                # existing rectangle - update the existing one
                self.update_rectangle(in_rect.get("uuid"), bbox)
            else:
                # new rectangle - add to self.rectangles
                new_rect = {
                    "bbox": bbox,
                    "id": in_rect.get("uuid")
                }
                self.rectangles.append(new_rect)

        # for r in self.rectangles:
        #     if not self.headless:
        #         # In GUI mode
        #         rect_id = self.object_mapping[r]

        #         for obj in in_rects:
        #             if rect_id == obj.get("uuid"):
        #                 # existing rectangle


    def create_gui(self):
        """Create the Tk GUI elements if we are not running in 'headless' mode.
        Typically used to verify the position of the camera and the regions of interest.
        """
        self.root = Tk()
        self.canvas = Canvas(self.root, width=640, height=480, bd=10, bg='white')
        self.canvas.focus_set()
        self.canvas.pack(expand=YES, fill=BOTH)
        self.canvas.bind("<ButtonPress-3>", self.on_right_button_press)
        self.canvas.bind("<ButtonPress-1>", self.on_button_single_press)
        self.canvas.bind("<Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Key>", self.on_key)
        self.canvas.grid(row=0, column=0, columnspan=2)

        # Benjamin Buttons..
        b = Button(width=10, height=1, text='Quit', command=self.quit)
        b.grid(row=1, column=0)

        b2 = Button(width=10, height=1, text='Clear', command=self.clear)
        b2.grid(row=1, column=1)

        btn_save = Button(width=10, height=1, text='Save', command=self.save)
        btn_save.grid(row=2, column=0)

    def save(self):
        """Save all rectangles to a config file (json)."""

        ws_payload = []
        with open('config.json', 'w') as cfg_file:
            data = {'rectangles': []}
            for rect in self.rectangles:
                rect_id = self.object_mapping[rect]
                bbox = self.get_bbox(rect)
                x0, y0, x1, y1 = bbox
                data["rectangles"].append({
                    "id": str(rect_id),
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1
                })

                ws_payload.append({
                    "bbox": (x0, y0, x1, y1),
                    "id": rect_id
                })

            # Write dictionary to cfg_file (json serialized)
            json.dump(data, cfg_file)

        print("kattvhask ws_payload: {}".format(ws_payload))
        # UGLY trick: we wan't to avoid an 'update' event on the
        #           web_server.kattvhask_setup object. Therefore
        #           removing our listener before updating the value.
        #           Then add our 'self.on_setup_update' callback again.
        # web_server.kattvhask_setup.remove_bind(self.on_setup_update)
        # web_server.kattvhask_setup.rectangles = ws_payload
        # web_server.kattvhask_setup.bind_to(self.on_setup_update)
        self.setup_queue.put(ws_payload)

    def clear(self):
        self.active_rect = None
        for item in self.rectangles:
            self.canvas.delete(item)
        self.rectangles = []
        self.object_mapping.clear()

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
        # print("on_button_single_click: canvasxy({}, {}), event.xy=({}, {})".format(curX, curY, event.x, event.y))

        rectangle_under_cursor = self.get_rectangle_at_point(curX, curY)
        if not rectangle_under_cursor:
            # No rectangle under cursor
            rect = self.canvas.create_rectangle(curX, curY, curX, curY, outline='green', width=self.rect_border_width, tags="rectangle")
            self.rectangles.append(rect)
            rect_id = uuid.uuid4()
            self.object_mapping[rect] = rect_id
            self.active_rect = rect
        else:
            if self.active_rect:
                self.canvas.itemconfig(self.active_rect, outline='red')
            self.active_rect = rectangle_under_cursor
            self.canvas.itemconfig(self.active_rect, outline='green')
            click_rect_border = self.cursor_at_rectangle_border(curX, curY, rectangle_under_cursor)
            if click_rect_border:
                # print("Border was clicked")
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
        widget = event.widget
        widget.focus_set()

    def quit(self):
        if not self.headless:
            self.root.destroy()

        self.capture.stop()

    def init_video_stream(self):
        import imutils.video
        if utils.is_raspberry_pi():
            LOG.info("Running Raspberry Pi")
            self.capture = imutils.video.VideoStream(usePiCamera=True)
        else:
            LOG.info("Running regular x86")
            # self.capture = cv2.VideoCapture(0)
            self.capture = imutils.video.VideoStream()

        # start video capture thread
        self.capture.start()

        # Warmup time
        time.sleep(1)

    def do_detect(self, frame):
        """
        This method calculates and identifies actual movement inside the
        regions of interest.

        If movement is identified a video capture will be written to the
        designated output area based on the current date and timestamp.

        Return False / True
        """
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

            # minimum 5 good frames before tag as 'motion'
            if self.good_contours_count > 5:
                x, y, w, h = cv2.boundingRect(c)
                if not self.headless:
                    # draws a green rectangle surrounding the contour with motion
                    cv2.rectangle(frame, (x, y), (x + w, y + w), (0, 255, 0), 2)

                if not self.kcw.recording:
                    LOG.info(f"Detected: {x}, {y} {w} {h}")
                    video_writer = cv2.VideoWriter_fourcc(*"DIVX")
                    fps = 20
                    self.kcw.start(video_writer, fps)

                # trigger new websocket message
                self.notify_motion()

                self.last_contour_identified = pendulum.now()

        if found_contours_in_frame == 0 and self.motion_detected and self.kcw.recording:
            now = pendulum.now()
            # since_start = now - self.kcw.start_time
            since_start = now - self.last_contour_identified
            if since_start.seconds > 4 and self.kcw.recording:
                LOG.info("5 seconds after no motion detected. Stop recording.")
                self.kcw.finish()
                LOG.info(f"No movement... Good contours: {self.good_contours_count}")
                self.motion_detected = False
                self.good_contours_count = 0

        # Always store frame in circular buffer
        self.kcw.update(frame)

    def notify_motion(self):

        async def send_alert():
            """
            coroutine that will construct the 'event' to pass to our
            async websocket server.
            """
            ts = pendulum.now()
            event = {
                "when": str(ts),
                "body": "Motion detected"
            }
            print(f"motion detection alert")
            await web_server.queue.put(event)


        if self.last_notification is not None:
            period = pendulum.now() - self.last_notification
            # if period.seconds < 5:
            if period.seconds < 1:
                return
            else:
                self.last_notification = pendulum.now()
        else:
            self.last_notification = pendulum.now()

        # Pass the coroutine to our asyncio event loop for execution
        asyncio.run_coroutine_threadsafe(send_alert(), loop=self.loop)

        if self.mqtt:
            ts = pendulum.now()
            event = {
                "when": ts,
                "body": "Motion detected"
            }
            self.mqtt(event)

    async def ws_send_rectangles(self):
        await web_server.queue.put("LOL")

    def run(self):
        async def send_frame_to_webserver(frame):
            await web_server.frames.put(bytes(frame))

        try:
            last_frame_ts = pendulum.now()
            while True:
                now = pendulum.now()
                frame = self.capture.read()
                if self.capture.stream.stopped:
                    LOG.info("Videostream stopped.")
                    break
                # if not frame:
                #     if not self.capture.isOpened():
                #         break
                #     else:
                #         continue

                gray_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                gray_and_blurred = cv2.GaussianBlur(gray_frame, (21, 21), 0)

                # initialize accumulation
                if self.image_acc is None:
                    self.image_acc = gray_and_blurred.copy().astype("float")

                # Update frame queue
                self.frame_queue.append(gray_and_blurred)

                self.do_detect(frame)

                # Output a video frame every second
                elapsed = now - last_frame_ts
                if elapsed.seconds >= 1:
                    _, jpg_frame = cv2.imencode('.png', frame)
                    b64 = base64.b64encode(jpg_frame)

                    asyncio.run_coroutine_threadsafe(send_frame_to_webserver(b64), loop=self.loop)
                    last_frame_ts = pendulum.now()

                if not self.headless:
                    img = Image.fromarray(frame)
                    b, g, r = img.split()
                    img = Image.merge("RGB", (r, g, b))
                    photo = ImageTk.PhotoImage(image=img)
                    if not self.image:
                        self.image = self.canvas.create_image(0, 0, image=photo, anchor=NW, tags="photo")

                        # Need to parse config after the initial image is set. Or else our rectangles
                        # won't be drawn on top of the image canvas.
                        self.parse_config()
                    else:
                        self.canvas.itemconfig(self.image, image=photo)
                    self.root.update()

                try:
                    input_change_from_websocket = self.input_changes.get_nowait()
                    if input_change_from_websocket is not None:
                        self.on_input_change(input_change_from_websocket)
                except queue.Empty:
                    pass

            if not self.headless:
                self.root.mainloop()

        except KeyboardInterrupt as err:
            LOG.info("User ctrl+c'ed us.. Time to quit!")
            self.quit()
            raise err


@click.command()
@click.option('--loglevel',
             default='INFO',
             type=click.Choice(
                 ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
             ),
             help="The level of logging output to include")
@click.option("--config",
             default=None,
             type=click.Path(exists=False, file_okay=True, dir_okay=False, resolve_path=True),
             help='Configuration file')
@click.option('--headless',
             default=False,
             is_flag=True,
             type=bool,
             help="If true then run in headless mode (without any GUI)")
@click.option('--mqtt-host',
             default=None,
             help="Hostname / IP of MQTT server")
@click.option('--mqtt-username',
             default=None,
             help="MQTT username")
@click.option('--mqtt-pw',
             default=None,
             help="MQTT password")
def main(loglevel, config, headless, mqtt_host, mqtt_username, mqtt_pw):
    logconfig.init(loglevel=getattr(logging, loglevel))
    if not imutils.is_cv3():
        LOG.info("Kattvhask needs OpenCV 3.X")
        sys.exit(1)

    LOG.info("Start websocket server..")
    new_loop = asyncio.new_event_loop()

    def start_loop(loop):
        asyncio.set_event_loop(loop)

        LOG.info("Start asyncio in threaded loop..")
        loop.run_forever()

    def shutdown_task():
        LOG.info("Shutdown loop")
        loop = asyncio.get_event_loop()
        all_tasks = asyncio.Task.all_tasks(loop=loop)
        asyncio.gather(loop=loop, *all_tasks, return_exceptions=True).cancel()

    LOG.info("Creating and starting backgrund thread..")
    webserver_ready = Event()
    t = Thread(target=web_server.start_server, args=(new_loop, webserver_ready))
    t.start()

    LOG.info("Waiting for webserver..")
    webserver_ready.wait()
    LOG.info("Ready!")

    try:
        cfg = None
        if config:
            with open(config, 'r') as f:
                try:
                    cfg = json.load(f)
                except json.decoder.JSONDecodeErrors:
                    LOG.warn("Unable to parse config file.")

        mqtt_handler = None
        if mqtt_host:
            mqtt_handler = handlers.Mqtt("kattvhask", mqtt_host, mqtt_username, mqtt_pw)

        app = Kattvhask(new_loop, config=cfg, headless=headless, mqtt=mqtt_handler, setup_queue=web_server.setup_queue)
        app.run()

    except KeyboardInterrupt:
        pass

    finally:
        LOG.info("GUI quited..")
        new_loop.call_soon_threadsafe(shutdown_task)
        new_loop.stop()

    # Ensure that async thread is done
    t.join()

if __name__ == "__main__":
    main()
