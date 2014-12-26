#!/usr/bin/env python
from select import select
from time import time
from os.path import exists
from os import listdir
from ConfigParser import RawConfigParser
from Image import frombytes, open as fromfile
from ImageTk import PhotoImage
from ImageOps import invert, autocontrast, grayscale
from Tkinter import Frame, Button, Tk, Label, Canvas, BOTH, TOP, Checkbutton, OptionMenu, StringVar, BooleanVar
from v4l2capture import Video_device

'''
webcam liveview and single picture capture program. this program shows a
picture in low resolution. when triggered (by 'space', 'enter' or the button)
it switches the webcam to a high resolution to take a picture and stores it.
after that it switches back to the liveview mode in low resulution.

the filename for storage is counted up by pic no and role (which is aa, ab,
ac...). it tries to determine the next pic no to not overwrite existing files.
is stores the scans in the current directory.

this program is good to be used with scanners for analog film rolls where you
manually position the picture with a live view and scan in highest possible
resolution.

it needs tkinter (see http://effbot.org/tkinterbook/tkinter-index.htm), pil
image, imageops and imagetk and the famous v4l2capture.

TODO:
- set v4l properties (contrast, hue, sat, ..)
- get event from usb dev
- reduce redundant code
'''

def ascii_increment(val):
	' count aa, ab, ac ... '
	a = ord('a')
	i = (ord(val[0]) - a) * 26 + (ord(val[1]) - a)
	i += 1
	return chr(a + i / 26) + chr(a + i % 26)

class Cap(Frame):
	def __init__(self):
		' set defaults, create widgets, bind callbacks, start live view '
		# go!
		self.root = Tk()
		self.root.bind('<Destroy>', self.stop_video)
		self.root.bind("<space>", self.single_shot)
		self.root.bind("<Return>", self.single_shot)
		self.root.bind("q", self.quit)
		# config:
		self.config = RawConfigParser()
		self.config.read('filmroller.conf')
		if not self.config.has_section('global'):
			self.config.add_section('global')
		self.video = None
		self.invert = BooleanVar(name='invert')
		self.invert.set(self.config_get('invert', True))
		self.invert.trace("w", self.configure)
		self.bw = BooleanVar(name='bw')
		self.bw.set(self.config_get('bw', False))
		self.bw.trace("w", self.configure)
		self.auto = BooleanVar(name='auto')
		self.auto.set(self.config_get('auto', True))
		self.auto.trace("w", self.configure)
		self.videodevice = StringVar(name='videodevice')
		dev_names = sorted(['/dev/{}'.format(x) for x in listdir("/dev") if x.startswith("video")])
		self.videodevice.set(self.config_get('videodevice', dev_names[-1]))
		self.videodevice.trace("w", self.configure)
		#
		Frame.__init__(self, self.root)
		self.pack()
		self.canvas = Canvas(self, width=640, height=480, )
		self.canvas.pack(side='top')
		self.xt = Checkbutton(self, text='Invert', variable=self.invert)
		self.xt.pack(side='left')
		self.xb = Checkbutton(self, text='B/W', variable=self.bw)
		self.xb.pack(side='left')
		self.xa = Checkbutton(self, text='Auto', variable=self.auto)
		self.xa.pack(side='left')
		self.xv = OptionMenu(self, self.videodevice, *dev_names, command=self.restart_video)
		self.xv.pack(side='left')
		self.resetrole = Button(self, text='First role', command=self.first_role)
		self.resetrole.pack(side='left')
		self.fnl = Label(self)
		self.fnl.pack(side='left')
		self.nextrole = Button(self, text='Next role', command=self.inc_role)
		self.nextrole.pack(side='left')
		self.take = Button(self, text='Take!', command=self.single_shot)
		self.take.pack(side='right')
		self.first_role()
		self.start_video()

	def config_get(self, name, default):
		' read a configuration entry, fallback to default if not already stored '
		if not self.config.has_option('global', name):
			return default
		if isinstance(default, bool):
			return self.config.getboolean('global', name)
		else:
			return self.config.get('global', name)

	def configure(self, name, mode, cbname):
		' change a configuration entry '
		if cbname == 'w':
			value = getattr(self, name).get()
			self.config.set('global', name, str(value))
			self.config.write(open('filmroller.conf', 'w'))

	def first_role(self):
		' jump back to first role '
		self.role = 'aa'
		self.serial = 0
		self.inc_picture()

	def inc_picture(self):
		' increment the picture number, jump over existing files '
		self.filename = 'scanned.{}-{:04}.jpg'.format(self.role, self.serial, )
		while exists(self.filename):
			self.serial += 1
			self.filename = 'scanned.{}-{:04}.jpg'.format(self.role, self.serial, )
		self.root.title('filmroller - ' + self.filename)
		self.fnl['text'] = self.filename
		self.root.title('filmroller - ' + self.filename)

	def inc_role(self):
		' increment to next role '
		self.serial = 0
		self.role = ascii_increment(self.role)
		self.inc_picture()

	def set_pauseimage(self):
		' show pause image (during shot) '
		self.image = fromfile('filmroller.pause.png')
		self.image.thumbnail((self.previewsize['size_x'], self.previewsize['size_y'], ), )
		self.photo = PhotoImage(self.image)
		self.canvas.create_image(self.previewsize['size_x']/2, self.previewsize['size_y']/2, image=self.photo)

	def quit(self, event):
		' quit program '
		self.root.destroy()

	def stop_video(self, *args):
		' stop video and release device '
		if self.video is not None:
			self.video.stop()
			self.video.close()
			self.video = None

	def restart_video(self, *args):
		' restart video (if device changes or hangs) '
		self.stop_video()
		self.root.after(1, self.start_video)

	def start_video(self, *args):
		' init video and start live view '
		if self.video is None:
			self.video = Video_device(self.videodevice.get())
			_, _, self.fourcc = self.video.get_format()
			caps = sorted(self.video.get_framesizes(self.fourcc), cmp=lambda a, b: cmp(a['size_x']*a['size_y'], b['size_x']*b['size_y']))
			self.previewsize, self.highressize = caps[0], caps[-1]
			self.previewsize['size_x'], self.previewsize['size_y'] = self.video.set_format(
				self.previewsize['size_x'], self.previewsize['size_y'], 0, 'MJPEG')
			try: self.video.set_auto_white_balance(True)
			except: pass
			try: self.video.set_exposure_auto(True)
			except: pass
			try: self.video.set_focus_auto(True)
			except: pass
			self.video.create_buffers(30)
			self.video.queue_all_buffers()
			self.video.start()
			self.root.after(1, self.live_view)
			#self.canvas.width=640
			#self.canvas.height=480
			#self.canvas.pack(side='top')

	def live_view(self, delta=3.0):
		' show single pic live view and ask tk to call us again later '
		if self.video is not None:
			select((self.video, ), (), ())
			data = self.video.read_and_queue()
			self.image = frombytes('RGB', (self.previewsize['size_x'], self.previewsize['size_y']), data)
			if self.invert.get():
				self.image = invert(self.image)
			if self.bw.get():
				self.image = grayscale(self.image)
			if self.auto.get():
				self.image = autocontrast(self.image)
			self.photo = PhotoImage(self.image)
			self.canvas.create_image(self.previewsize['size_x']/2, self.previewsize['size_y']/2, image=self.photo)
			self.root.after(1, self.live_view)

	def single_shot(self, *args):
		' do a high res single shot and store it '
		def go():
			self.video = Video_device(self.videodevice.get())
			try:
				self.highressize['size_x'], self.highressize['size_y'] = self.video.set_format(
					self.highressize['size_x'], self.highressize['size_y'], 0, 'MJPEG')
				try: self.video.set_auto_white_balance(True)
				except: pass
				try: self.video.set_exposure_auto(True)
				except: pass
				try: self.video.set_focus_auto(True)
				except: pass
				self.video.create_buffers(7)
				self.video.queue_all_buffers()
				self.video.start()
				for n in range(7): # wait for auto
					select((self.video, ), (), ())
					data = self.video.read_and_queue()
				image = frombytes('RGB', (self.highressize['size_x'], self.highressize['size_y'], ), data)
				if self.invert.get():
					image = invert(image)
				if self.bw.get():
					image = grayscale(image)
				if self.auto.get():
					image = autocontrast(image)
				image.save(self.filename)
				self.inc_picture()
				self.video.stop()
			finally:
				self.video.close()
				self.video = None
			self.root.after(1, self.start_video)
		self.stop_video()
		self.set_pauseimage()
		self.root.after(1, go)


def main():
	' main start point of the program '
	app = Cap()
	app.mainloop()

main()
