from datetime import datetime
import os.path
import sys
from subprocess import call
import signal
import time

import pyinotify

import classifyImg
classifyImg=classifyImg.classifyImg

db=tobedefined

log_file = open("%s/var/log/iphoneMediaMon.log" %db, "w")


def log(text):
	dt = datetime.utcnow().isoformat()
	log_file.write(dt + ' - ' + text + "\n")
	log_file.flush()


def signal_handler(signal, frame):
	log("Exiting")
	sys.exit(0)


log("Starting")

signal.signal(signal.SIGTERM, signal_handler)

watched_paths = ["/volume1/photo/Iphone"]

allowed_exts = {
	"jpg",
	"jpeg",
	"png",
	"tga",
	"gif",
	"bmp",
	"mp3",
	"flac",
	"aac",
	"wma",
	"ogg",
	"ogv",
	"mp4",
	"avi",
	"m4v",
	"mkv",
	"mov",
}

wm = pyinotify.WatchManager()
mask = (
	pyinotify.IN_CLOSE_WRITE
)


class EventHandler(pyinotify.ProcessEvent):
	def __init__(self):
		pass

	def process_IN_CLOSE_WRITE(self, event):
		self.process_create(event)

#	def process_IN_CREATE(self, event):
#		self.process_create(event)

	def process_create(self, event):
		if event.maskname == 'IN_CREATE':
			return
		arg = ''
		if event.dir:
			pass
		else:
			self.do_classify_command(event)

	def do_classify_command(self, event):
		if self.is_allowed_path(event.pathname, event.dir):
			log("classify %s %s" % (event.maskname, event.pathname))
			time.sleep(1)
			if os.path.exists(event.pathname) and os.path.getsize(event.pathname) > 0:
				log(classifyImg(event.pathname))
		else:
			log("%s is not an allowed path" % event.pathname)

	def is_allowed_path(self, filename, is_dir):
		# Don't check the extension for directories
		if not is_dir:
			ext = os.path.splitext(filename)[1][1:].lower()
			if ext not in allowed_exts:
				return False
		if filename.find("@eaDir") > 0:
			return False
		return True

handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)
wdd = wm.add_watch(
	watched_paths,
	mask,
	rec=True,
	auto_add=True,
	exclude_filter=lambda p: '/@' in p
)

try:
	notifier.loop(daemonize=True, pid_file='/var/services/homes/afawaz/var/run/iphoneMediaMon.pid')
except pyinotify.NotifierError as err:
	log(str(err))

