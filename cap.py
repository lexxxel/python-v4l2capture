#!/usr/bin/env python
from Image import frombytes, open as fromfile
from ImageTk import PhotoImage
from ImageChops import invert
from select import select
from v4l2capture import Video_device
from time import time
from Tkinter import Frame, Button, Tk, Label, Canvas, BOTH, TOP

class Cap(Frame):
	def __init__(self):
		self.root = Tk()
		Frame.__init__(self, self.root)
		self.pack()
		self.image = fromfile('image.png')
		self.photo = PhotoImage(self.image)
		self.canvas = Canvas(self, width=640, height=480, )
		self.canvas.create_image(320, 240, image=self.photo)
		self.canvas.pack() #self.canvas.pack(side=TOP, expand=True, fill=BOTH)
		self.take = Button(self, text="take", fg="red", command=self.start_view)
		self.take.pack(side="bottom")
		#self.QUIT = Button(self, text="QUIT", fg="red", command=root.destroy)
		self.video = None

	def start_view(self):
		if self.video:
			self.video.stop()
			self.video.close()
			self.video = None
		else:
			self.video = Video_device("/dev/video0")
			self.video.set_format(640, 480)
			self.video.create_buffers(30)
			self.video.queue_all_buffers()
			self.video.start()
			self.root.after(0, self.live_view)

	def live_view(self, delta=3.0):
		if self.video:
			#size_x, size_y, mode = self.video.get_format() # YCbCr
			select((self.video,), (), ())
			data = self.video.read_and_queue()
			self.image = frombytes('RGB', (640, 480), data)
			#self.image = invert(self.image)
			self.photo = PhotoImage(self.image)
			self.canvas.create_image(320, 240, image=self.photo)
			self.root.after(1, self.live_view)

	def single_shot(self):
			size_x, size_y = self.video.set_format(2592, 1944)
			mode = 'RGB'
			#size_x, size_y, mode = self.video.get_format() # YCbCr
			self.video.create_buffers(1)
			self.video.queue_all_buffers()
			self.video.start()
			select((self.video, ), (), ())
			data = self.video.read()
			image = frombytes(mode, (size_x, size_y), data)
			#image = invert(image)
			image.save("scanned.jpg")
			self.video.stop()

	def video_take(self, delta=3.0):
		self.video = Video_device("/dev/video0")
		try:
			size_x, size_y = self.video.set_format(640, 480, fourcc='MJPG')
			self.video.create_buffers(30)
			self.video.queue_all_buffers()
			self.video.start()
			stop_time = time() + delta
			with open('video.mjpg', 'wb') as f:
				while stop_time >= time():
					select((self.video,), (), ())
					data = self.video.read_and_queue()
					f.write(data)
			self.video.stop()
		finally:
			self.video.close()

app = Cap()
app.mainloop()
exit(0)
