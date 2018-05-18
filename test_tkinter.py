#!/usr/bin/env python

from tkinter import *
import cv2
from PIL import Image, ImageTk
import time


class Kattvhask:

    def __init__(self):
        self.root = None
        self.capture = None
        self.rect = None
        self.image = None
        self.rectangles = []
        self.active_rect = None
        self.moving = False
        self.prev_curX = None
        self.prev_curY = None

        self.create_gui()
        self.init_video_stream()

    def create_gui(self):
        self.root = Tk()
        self.canvas = Canvas(self.root, width=500, height=300, bd=10, bg='white')
        self.canvas.focus_set()
        self.canvas.pack(expand=YES, fill=BOTH)
        # self.canvas.bind("<Button-1>", self.callback)
        # self.canvas.bind("<Double-Button-1>", self.on_button_double_click)
        self.canvas.bind("<ButtonPress-3>", self.on_right_button_press)
        self.canvas.bind("<ButtonPress-1>", self.on_button_single_press)
        self.canvas.bind("<Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Key>", self.on_key)
        self.canvas.grid(row=0, column=0, columnspan=2)

        b = Button(width=10, height=2, text='Quit', command=self.quit)
        b.grid(row=1, column=0)
        b2 = Button(width=10, height=2, text='Clear', command=self.clear)
        b2.grid(row=1, column=1)

    # def on_button_double_click(self, event):
    #     print("on_button_double_click")
    #     self.rect_start_x = self.canvas.canvasx(event.x)
    #     self.rect_start_y = self.canvas.canvasy(event.y)

    #     rectangle_under_cursor = self.get_rectangle_at_point(self.rect_start_x, self.rect_start_y)
    #     if not rectangle_under_cursor:
    #         # No rectangle under cursor
    #         rect = self.canvas.create_rectangle(self.rect_start_x, self.rect_start_y, self.rect_start_x - 20, self.rect_start_y - 20, outline='green', width=5.0)
    #         self.rectangles.append(rect)
    #         self.active_rect = rect
    #     else:
    #         self.active_rect = rectangle_under_cursor
    #         self.canvas.itemconfig(self.active_rect, outline='green')

    def clear(self):
        print("Clear all rectangles")
        self.active_rect = None
        for item in self.rectangles:
            self.canvas.delete(item)
        self.rectangles = []

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
                    print("Mouse inside item {}".format(item))
                    return item
        return None

    def cursor_at_rectangle_border(self, curX, curY, rectangle):
        """Returns true if the click was nearby the rectangle's border, else false"""
        bbox = self.canvas.bbox(rectangle)
        x0, y0, x1, y1 = bbox
        item_width = int(float(self.canvas.itemcget(rectangle, "width")))

        min_x_boundary = range(x0 - item_width, x0 + item_width)
        max_x_boundary = range(x1 - item_width, x1 + item_width)
        min_y_boundary = range(y0 - item_width, y0 + item_width)
        max_y_boundary = range(y1 - item_width, y1 + item_width)

        if curX in min_x_boundary:
            # left side
            if curY >= y0 - item_width and curY <= y1 + item_width:
                # inside rectangle, so good
                return True

        if curX in max_x_boundary:
            # right side
            if curY >= y0 - item_width and curY <= y1 + item_width:
                # inside rectangle, so good
                return True

        if curY in min_y_boundary:
            # top
            if curX >= x0 - item_width and curX <= x1 + item_width:
                return True

        if curY in max_y_boundary:
            # bottom
            if curX >= x0 - item_width and curX <= x1 + item_width:
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
            print("on_button_single_press: No rectangle under cursor.")
            rect = self.canvas.create_rectangle(curX, curY, curX, curY, outline='green', width=5.0, tags="rectangle")
            self.rectangles.append(rect)
            self.active_rect = rect
        else:
            print("on_button_single_press: Rectangle under cursor: {}".format(rectangle_under_cursor))
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
        print("on_button_single_press: rectangle_id = {}".format(self.active_rect))

    def on_button_release(self, event):
        print("on_button_release")

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
        print("Pressed: {}".format(event.char))
        if event.char == 'q':
            self.quit()

    def callback(self, event):
        widget = event.widget
        widget.focus_set()
        print("clicked x={ev.x}, y={ev.y}".format(ev=event))

    def quit(self):
        print("Quiting..")
        self.capture.release()
        self.root.destroy()

    def init_video_stream(self):
        self.capture = cv2.VideoCapture(0)
        # Warmup time
        time.sleep(1)

    def run(self):
        while True:
            grabbed, frame = self.capture.read()
            if not grabbed:
                if not self.capture.isOpened():
                    break
                else:
                    continue

            img = Image.fromarray(frame)
            b, g, r = img.split()
            img = Image.merge("RGB", (r, g, b))
            photo = ImageTk.PhotoImage(image=img)
            if not self.image:
                self.image = self.canvas.create_image(0, 0, image=photo, anchor=NW, tags="photo")
            else:
                self.canvas.itemconfig(self.image, image=photo)

            if cv2.waitKey(10) == 27:
                break

            self.root.update()
        self.root.mainloop()


if __name__ == "__main__":
    app = Kattvhask()
    app.run()
