#!/usr/bin/env python
from Image import frombytes, open as fromfile
from ImageTk import PhotoImage
from ImageChops import invert
from select import select
from v4l2capture import Video_device
from time import time
from Tkinter import Frame, Button, Tk, Label, Canvas, BOTH, TOP
from os.path import exists
from evdev import InputDevice

# TODO:
# - determine serial
# - get v4l properties (sizes & fps)
# - set v4l properties (contrast, hue, sat, ..)
# - get event from usb dev

class Cap(Frame):
	def __init__(self):
		self.serial = 0
		self.invert = True
		self.videodevice = '/dev/video1'
		self.root = Tk()
		self.root.bind('<Destroy>', self.stop_video)
		Frame.__init__(self, self.root)
		self.pack()
		self.canvas = Canvas(self, width=640, height=480, )
		self.canvas.pack()
		self.take = Button(self, text='take!', fg='red', command=self.single_shot)
		self.take.pack(side='bottom')
		self.video = None
		self.start_video()

	def set_pauseimage(self):
		self.image = fromfile('image.png')
		self.photo = PhotoImage(self.image)
		self.canvas.create_image(320, 240, image=self.photo)

	def stop_video(self, *args):
		if self.video is not None:
			self.video.stop()
			self.video.close()
			self.video = None

	def start_video(self):
		if self.video is not None:
			self.stop_video()
		self.video = Video_device(self.videodevice)
		self.video.set_format(640, 480)
		self.video.create_buffers(30)
		self.video.queue_all_buffers()
		self.video.start()
		#width, height, mode = self.video.get_format() # YCbCr
		self.root.after(1, self.live_view)

	def live_view(self, delta=3.0):
		if self.video is not None:
			select((self.video,), (), ())
			data = self.video.read_and_queue()
			self.image = frombytes('RGB', (640, 480), data)
			if self.invert:
				self.image = invert(self.image)
			self.photo = PhotoImage(self.image)
			self.canvas.create_image(320, 240, image=self.photo)
			self.root.after(1, self.live_view)

	def single_shot(self):
		def go():
			self.video = Video_device(self.videodevice)
			try:
				width, height = self.video.set_format(2592, 1944)
				mode = 'RGB'
				self.video.create_buffers(1)
				self.video.queue_all_buffers()
				self.video.start()
				select((self.video, ), (), ())
				data = self.video.read()
				image = frombytes(mode, (width, height), data)
				if self.invert:
					image = invert(image)
				filename = 'scanned.{}.jpg'.format(self.serial)
				self.serial += 1
				image.save(filename)
				print filename, 'saved'
				self.video.stop()
			finally:
				self.video.close()
				self.video = None
			self.root.after(10, self.start_video)
		self.stop_video()
		self.set_pauseimage()
		self.root.after(10, go)


app = Cap()
app.mainloop()
exit(0)
