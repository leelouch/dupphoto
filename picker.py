#!/usr/bin/python3

# This code is available for use under CC0 (Creative Commons 0 - universal). 
# You can copy, modify, distribute and perform the work, even for commercial
# purposes, all without asking permission. For more information, see LICENSE.md or 
# https://creativecommons.org/publicdomain/zero/1.0/

import re, os, pdb, shutil
import curses
from curses import wrapper
curses.wrapper = wrapper
from curses.textpad import Textbox, rectangle
from classifyImg import classifyImg
from config import *
import exiftool

mainFooter  = "Space = toggle, Enter = delete, A/N = select all/None, f or / = regex filter, c = change order, s = show options, t = tag photo, k = classify, Esc/q = cancel/exit"
showFooter  = "x/X: show selected, a: show all"
swipeFooter = "0-9: put file at 0-9 position at first position, a: for auto"

class MediaInfo(object):
	def __init__(self, **args):
		self.meta = {}
		self.meta.update(args)

	def str(self, inline):
		ret  = "%s: %-30s%s %s: %s" %(
			"Tag", self.meta.get("tag", "")
		,	"" if inline else "\n"
		,	"Date", self.meta.get("date", "")
		)
		return ret

	def __bool__(self):
		return len(self.meta)>0
	__nonzero__ = __bool__

class Picker:
	"""Allows you to select from a list with curses"""
	stdscr = None
	win = None
	title = ""
	arrow = ""
	footer = ""
	more = ""
	c_selected = ""
	c_empty = ""

	cursor = 0
	offset = 0
	selected = 0
	selcount = 0
	aborted = False

	window_height = 15
	window_width = 60
	length = 0
	labelOfset = 5

	def curses_start(self):
		self.stdscr = curses.initscr()
		curses.noecho()
		curses.cbreak()
		self.win = curses.newwin(
			self.window_height,
			self.window_width,
			1,
			2
		)

		self.scrh, self.scrw = self.stdscr.getmaxyx()
		self.createWorkWindow()
		self.createGetWindow()

	def curses_stop(self):
		curses.nocbreak()
		self.stdscr.keypad(0)
		curses.echo()
		curses.endwin()

	def getSelected(self):
		if self.aborted == True:
			return( False )
		ret_s = filter(lambda x: x["selected"], self.all_options)
		ret   = map(lambda x: x["label"], ret_s)
		return( ret )

	def getRemoved(self):
		return self.removedList

	def clearSelected(self):
		ret_s = filter(lambda x: x["selected"], self.all_options)
		idx_s = map(lambda x: x["idx"], ret_s)

		for x in idx_s:
			self.log("clear selected: ", self.byIdx[x]['label'])
			self.removedList.append(self.byIdx[x]['label'].pop(0))
			if len(self.byIdx[x]['label'])<=1:
				self.byIdx.pop(x)
		self.refresh()

	def drawLine(self, h, w, msg, dec=curses.A_NORMAL):
		self.win.addstr(h, w, msg[0:min(len(msg), self.window_width-w-1)], dec)

	def redraw(self):
		self.scrh, self.scrw = self.stdscr.getmaxyx()
		self.window_height, self.window_width = self.scrh-2, self.scrw-4
		self.winDepth = self.window_height-4

		self.log("scr=", self.scrh, self.scrw, "win=", self.window_height, self.window_width, "depth=", self.winDepth, "offset=", self.offset, "cursor=", self.cursor)

		self.win.clear()
		self.win.resize(self.window_height, self.window_width)
		self.win.border(
			self.border[0], self.border[1]
		,	self.border[2], self.border[3]
		,	self.border[4], self.border[5]
		,	self.border[6], self.border[7]
		)
		self.win.refresh()

		self.drawLine(self.window_height-1, 5," " + self.footer + " ")

		position = 0
		range = self.all_options[self.offset:self.offset+self.winDepth]
		for option in range:
			if self.showMetaData and option["metadata"]:
				s = "%-100s %s" %(option["label"][0], option["metadata"].str(inline=True))
			else:
				s = "".join([ "%-80s" %x for x in option["label"][option["offset"]:] ])

			decoration = curses.A_STANDOUT if self.cursor == position else curses.A_NORMAL
			if option["selected"] == True:
				self.drawLine(position + 2, self.labelOfset, "%s %s" %(self.c_selected, s), curses.A_BOLD | decoration)
				#self.win.addstr(position + 2, self.labelOfset, "%s %s" %(self.c_selected, s), curses.A_BOLD | decoration)
			else:
				self.drawLine(position + 2, self.labelOfset, "%s %s" %(self.c_empty   , s), decoration)
				#self.win.addstr(position + 2, self.labelOfset, "%s %s" %(self.c_empty   , s), decoration)

			position = position + 1

		# hint for more content above
		if self.offset > 0:
			self.win.addstr(1, 5, self.more)

		# hint for more content below
		if self.offset + self.winDepth < self.length:
			self.win.addstr(self.window_height-2, 5, self.more)

		self.win.addstr(0, 5, " " + self.title + " ")
		self.win.addstr(
			0, self.window_width - 8,
			" " + str(self.selcount) + "/" + str(self.length) + " "
		)
		self.win.addstr(self.cursor + 2,1, self.arrow)
		self.win.refresh()

	def check_cursor_up(self):
		if self.cursor < 0:
			self.cursor = 0
			if self.offset > 0:
				self.offset = self.offset - 1

	def check_cursor_down(self):
		if self.cursor >= self.length:
			self.cursor = self.cursor - 1

		if self.cursor >= self.winDepth-1:
			self.cursor = self.winDepth-1
			self.offset = self.offset + 1

			if self.offset + self.cursor >= self.length:
				self.offset = self.offset - 1

	def confirmWindow(self, msg):
		nLine  = 1
		nCol   = 30
		y      = self.scrh//2 - 1
		x      = self.scrw//2 - 1 - nCol//2
		self.askWin = curses.newwin(nLine, nCol, y, x)
		rectangle(self.stdscr, y-1, x-1, y+nLine, x+nCol)
		self.stdscr.refresh()
		self.askWin.addstr(0, 1, msg)
		c = self.askWin.getch()
		ret = c == ord("y")
		self.askWin.clear()
		return ret

	def createWorkWindow(self):
		nLine  = 2
		nCol   = 100
		y      = self.scrh//2 - 1
		x      = self.scrw//2 - 1 - nCol//2
		self.workWin = curses.newwin(nLine, nCol, y, x)

	def createGetWindow(self):
		offset = 40
		width  = 30
		self.textWin = curses.newwin(1, width, 1, offset)

	def showWorkMsgRectangle(self):
		nLine  = 2
		nCol   = 100
		y      = self.scrh//2 - 1
		x      = self.scrw//2 - 1 - nCol//2
		rectangle(self.stdscr, y-1, x-1, y+nLine, x+nCol)
		self.stdscr.refresh()

	def showGetRectangle(self):
		offset = 40
		width  = 30
		rectangle(self.stdscr, 0, offset-1, 1+0+1, offset+width)
		self.stdscr.refresh()

	def showMsg(self, msg, wait=True):
		self.showWorkMsgRectangle()
		self.workWin.addstr(0, 1, str(msg))
		self.workWin.refresh()
		if wait:
			self.workWin.getch()
			self.workWin.clear()

	def getText(self, dflt=""):
		offset = 40
		width  = 30
		self.showGetRectangle()
		self.textWin.addstr(0,0,dflt)
		box = Textbox(self.textWin)
		box.edit()
		message = box.gather()
		self.textWin.clear()
		return message.strip()

	def refresh(self):
		self.all_options = []
		for idx, d in self.byIdx.items():
			option = d['label']
			if not self.filterMsg or self.filterPat.match(" ".join(option)):
				self.all_options.append(d)
		self.length = len(self.all_options)
		self.cursor = 0
		self.offset = 0
		self.stdscr.clear()
		self.stdscr.refresh()

	def swipeIdx(self, idx, l):
		if idx >= len(l):
			return
		l.insert(0, l[idx])
		l.pop(idx+1)

	def curses_loop(self, stdscr):
		while 1:
			self.redraw()
			c = stdscr.getch()
			self.log("key=", c, chr(c) if c >=0 else c)

			if c == ord('q') or c == ord('Q') or c == 27:
				if self.confirmWindow("quit  (y/n) ? "):
					self.aborted = True
					break
			if self.selectIdx:
				if c == ord('a'):
					for x in self.all_options:
						if self.selectedOrd in x['label']:
							idx = x['label'].index(self.selectedOrd)
							if idx:
								self.swipeIdx(idx, x['label'])
				elif chr(c) in [ ('%d' %x) for x in range(9) ]:
					for x in self.all_options:
						if x["selected"]:
							self.swipeIdx(int(chr(c)), x['label'])
				else:
					self.log(chr(c), "not in range",  [ ('%d' %x) for x in range(9) ])
				self.selectIdx = False
				self.footer = mainFooter
			elif self.showAction:
				if c == ord('x'):
					self.all_options = []
					for idx, d in self.byIdx.items():
						option = d['label']
						if d['selected']:
							self.all_options.append(d)
					self.cursor = 0
					self.offset = 0
				elif c == ord('a'):
					self.all_options = []
					for idx, d in self.byIdx.items():
						self.all_options.append(d)
					self.cursor = 0
					self.offset = 0
				self.length = len(self.all_options)
				self.stdscr.clear()
				self.stdscr.refresh()
				self.showAction = False
				self.footer = mainFooter
			elif c == ord('i'):
				option = self.all_options[self.cursor]
				if not option["metadata"]:
					self.log("get meta data for", option["label"][0])
					option["metadata"] = self.getMediaInfo(option['label'][0])
				self.showMsg(option["metadata"].str(inline=False))
				self.stdscr.clear()
				self.stdscr.refresh()
			elif c in [ ord('m'), ord('M') ]:
				force = c == ord('M')
				self.showMetaData = not self.showMetaData
				for option in self.all_options:
					if option["selected"]:
						if force or not option["metadata"]:
							option["metadata"] = self.getMediaInfo(option['label'][0])
							self.showMsg("tag %s" %option['label'][0], wait=False)
							self.workWin.clear()
			elif c in [ ord(x) for x in [ 'f', '/', 'F' ] ]:
				self.filterMsg=self.getText(self.filterMsg if c == ord("/") else "")
				self.filterPat = re.compile(".*%s.*" %self.filterMsg.strip())
				self.refresh()
			elif c == ord('A'):
				for x in self.all_options:
					x["selected"] = True
			elif c == ord('N'):
				for x in self.all_options:
					x["selected"] = False
			elif c == ord('c'):
				self.selectIdx   = True
				self.selectedOrd = self.all_options[self.selected]["label"][0]
				self.log("select idx")
				self.footer = swipeFooter
			elif c == ord('k'):
				self.action(classifyImg, removeFromList=True, msg="classify %s ...")
				self.log("removedList=", self.removedList)
			elif c == ord('s'):
				self.footer = showFooter
				self.showAction = True
			elif c == ord('t'):
				tag = self.getText()
				if tag != "":
					self.showWorkMsgRectangle()
					for option in self.all_options:
						if option["selected"]:
							self.showMsg("tag %s" %option['label'][0], wait=False)
							option["metadata"].meta["tag"]= self.tag(tag, option['label'][0])
							self.workWin.clear()
				self.stdscr.clear()
				self.stdscr.refresh()
			elif c == curses.KEY_RIGHT:
				option = self.all_options[self.offset + self.cursor]
				nFile  = len(option["label"])
				option["offset"] = min(option["offset"] + 1, nFile-1)
			elif c == curses.KEY_LEFT:
				option = self.all_options[self.offset + self.cursor]
				option["offset"] = max(option["offset"] - 1, 0)
			elif c == curses.KEY_UP:
				self.cursor = self.cursor - 1
			elif c == curses.KEY_DOWN:
				self.cursor = self.cursor + 1
			elif c == curses.KEY_RESIZE:
				self.stdscr.clear()
				self.stdscr.refresh()
			elif c == curses.KEY_HOME:
				self.offset = 0
				self.cursor = 0
			elif c == curses.KEY_END:
				self.offset = self.length-self.winDepth
				self.cursor = self.winDepth - 1
			elif c == curses.KEY_PPAGE:
				self.offset = max(self.offset - self.winDepth, 0)
				if self.offset == 0:
					self.cursor = 0
			elif c == curses.KEY_NPAGE:
				self.log(self.offset, self.winDepth, self.length)
				self.offset = min(self.offset + self.winDepth, self.length-self.winDepth)
				self.log(self.offset)
				if self.offset < 0:
					self.offset = 0
					self.cursor = self.length
				elif self.offset == self.length-self.winDepth:
					self.cursor = self.winDepth - 1
			elif c == ord(' '):
				d = self.all_options[self.selected]
				d["selected"] = not d["selected"]
			elif c == 10:
				if self.confirmWindow("delete (y/n) ? "):
					self.action(self.remove, removeFromList=True, msg="removing %s ...")
				self.stdscr.clear()
				self.stdscr.refresh()

			# deal with interaction limits
			self.check_cursor_up()
			self.check_cursor_down()

			# compute selected position only after dealing with limits
			self.selected = self.cursor + self.offset

			temp = self.getSelected()
			self.selcount = len(list(temp))

	def getTag(self, filename):
		return self.et.get_tag("keywords", filename)

	def getDate(self, filename):
		date = self.et.get_tag("CreateDate", filename)
		return "" if date is None else date

	def tag(self, tag, filename):
		with self.et:
			newtag = tag
			curTag = self.et.get_tag("keywords", filename)
			if newtag!="!" and curTag is not None:
				if isinstance(curTag, list):
					tagList= set([ str(x) for x in curTag ])
				else:
					tagList= set([ x.strip() for x in curTag.split(",") ])
				tagList.add(tag)
				tagList = list(tagList)
				tagList.sort()
				newtag = ", ".join(tagList)
			if newtag == "!":
				newtag=""
			arg1 = ("-Keywords=%s" %newtag).encode("utf-8")
			arg2 = ("-Subject=%s"  %newtag).encode("utf-8")
			self.et.execute(arg1, arg2, filename.encode("utf-8"))
			return newtag

	def getMediaInfo(self, filename, inline=False):
		with self.et:
			tag  = self.getTag (filename)
			date = self.getDate(filename)
			tag  = tag if tag is not None else ""
			tag  = ", ".join([str(x) for x in tag]) if isinstance(tag, list) else str(tag)
			return MediaInfo(tag=tag, date=date)

	def remove(self, filename):
		dname = "%s/%s" %(backupDir, os.path.dirname(filename))
		if os.path.exists(filename):
			#print ("mv %s %s" %(filename, dname))
			if not os.path.exists(dname):
				os.makedirs(dname)
			shutil.move(filename, dname)
		else:
			self.log("%s not found, ignored ..." %(filename))

	def action(self, func, **keywords):
		self.showWorkMsgRectangle()
		selected = False
		removeFromList=keywords.pop("removeFromList", False)
		msg           =keywords.pop("msg", "%s %%s ..." %func)
		for i, option in enumerate(self.all_options):
			if option["selected"]:
				selected = True
				self.showMsg(msg %option['label'][0], wait=False)
				self.log(func(option['label'][0], **keywords))
				self.workWin.clear()
		if selected and removeFromList:
			self.clearSelected()
		self.stdscr.clear()
		self.stdscr.refresh()

	def initLog(self):
		pass
		self.logfile=open("pickerlog", 'w')

	def log(self, *args):
		if self.logEn:
			self.logfile.write(" ".join([str(x) for x in args]) + "\n")
			self.logfile.flush()

	def __init__(
		self,
		options,
		title='Select',
		log  = False,
		arrow="-->",
		footer=mainFooter,
		more="...",
		border="||--++++",
		c_selected="[X]",
		c_empty="[ ]"
	):
		self.title = title
		self.arrow = arrow
		self.footer = footer
		self.more = more
		self.border = border
		self.c_selected = c_selected
		self.c_empty = c_empty
		self.filterMsg  = ""
		self.showAction = False
		self.selectIdx  = False
		self.options    = options
		self.all_options = []
		self.byIdx       = {}
		self.et          = exiftool.ExifTool()
		self.logEn       = log
		self.showMetaData= False
		if self.logEn:
			self.initLog()

		for idx, option in enumerate(options):
			d = {
				"label"   : option
			,	"selected": False
			,	"idx"     : idx
			,	"metadata": MediaInfo()
			,	"offset"  : 0
			}
			self.byIdx[idx] = d
			self.all_options.append(d)
			self.length = len(self.all_options)

	def run(self):
		self.removedList = []

		self.curses_start()
		curses.wrapper( self.curses_loop )
		self.curses_stop()
