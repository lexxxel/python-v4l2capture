#!/usr/bin/env python
from Image import frombytes, open as fromfile
from ImageTk import PhotoImage
from ImageChops import invert
from select import select
from v4l2capture import Video_device
from time import time
from Tkinter import Frame, Button, Tk, Label, Canvas, BOTH, TOP
from threading import Thread

class Cap(Frame):
	def __init__(self):
		self.root = Tk()
		Frame.__init__(self, self.root)
		self.pack()
		self.createWidgets()

	def createWidgets(self):
		self.image = fromfile('image.png')
		#self.canvas=Canvas(root, width=1280, height=720, )
		#self.canvas.create_image(1280, 720, image=PhotoImage(self.image))
		#self.canvas.pack(side=TOP, expand=True, fill=BOTH)

		self.canvas = Label(self)
		self.photo = PhotoImage(self.image)
		self.canvas['image'] = self.photo
		self.canvas.pack()
		self.take = Button(self, text="take", fg="red", command=self.start_view)
		self.take.pack(side="bottom")
		#self.QUIT = Button(self, text="QUIT", fg="red", command=root.destroy)

	def start_view(self):
		Thread(target=self.update_picture).start()

	def single_shot(self):
		video = Video_device("/dev/video0")
		try:
			size_x, size_y = video.set_format(2592, 1944)
			mode = 'RGB'
			#size_x, size_y, mode = video.get_format() # YCbCr
			video.create_buffers(1)
			video.queue_all_buffers()
			video.start()
			select((video, ), (), ())
			data = video.read()
			image = frombytes(mode, (size_x, size_y), data)
			#image = invert(image)
			image.save("scanned.jpg")
			video.stop()
		finally:
			video.close()

	def update_picture(self, delta=3.0):
		video = Video_device("/dev/video0")
		try:
			size_x, size_y = video.set_format(640, 480)
			mode = 'RGB'
			#size_x, size_y, mode = video.get_format() # YCbCr
			video.create_buffers(30)
			video.queue_all_buffers()
			video.start()
			stop_time = time() + delta
			while stop_time >= time():
				select((video,), (), ())
				data = video.read_and_queue()
				self.image = frombytes(mode, (size_x, size_y), data)
				#self.image = invert(self.image)
				self.photo = PhotoImage(self.image)
				self.canvas['image'] = self.photo
			video.stop()
		finally:
			video.close()

	def video_take(self, delta=3.0):
		video = Video_device("/dev/video0")
		try:
			size_x, size_y = video.set_format(640, 480, fourcc='MJPG')
			video.create_buffers(30)
			video.queue_all_buffers()
			video.start()
			stop_time = time() + delta
			with open('video.mjpg', 'wb') as f:
				while stop_time >= time():
					select((video,), (), ())
					data = video.read_and_queue()
					f.write(data)
			video.stop()
		finally:
			video.close()

app = Cap()
app.mainloop()
exit(0)
