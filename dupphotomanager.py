#!/usr/bin/python3

import curses
import pickle
import picker
import sys, os
import shutil
import argparse

from picker import Picker
from curses import wrapper
from common import parseDir, computeSum

def getExt(f):
	idx = f.rfind('.')
	ext = ""
	if idx>=0:
		ext = f[idx+1:]
	return ext

def isMedia(f):
	ext = getExt(f)
	return ext and ext.lower() in [ "jpg", "png", "jpeg", "mov", "mp4", "mov" ]

class DupManager(object):
	def __init__(self, argv):
		parser     = argparse.ArgumentParser()

		parser.add_argument('-all' , action='store_true' , help='load all db, do not filter dup only')
		parser.add_argument('-log' , action='store_true' , help='verbose to log file')
		parser.add_argument('-test', action='store_true', help='for test only')
		parser.add_argument('--dir' , type=str, nargs="?" , help='create a db from directory', default="")
		parser.add_argument('db'   , type=str, nargs=1   , help='db filename')

		argList = argv[1:]
		args=parser.parse_args(argList)
		if not argList:
			parser.error("")

		self.db  = args.db[0]
		self.all = args.all
		self.test= args.test
		self.log = args.log
		self.dir = args.dir

		self.dbDict = {}

		if os.path.exists(self.db):
			self.loadDb(self.db)

		if self.dir:
			self.fillDbFromDir()


	def fillDbFromDir(self):
		"""
			create database from directory 
		"""	
		for f in parseDir(self.dir, excludeFunc= lambda x : not isMedia(x)):
			self.add2db(f)
		if self.db:
			self.saveDb()

	def add2db(self, f):
		sys.stdout.write(f)
		sys.stdout.write(" ... ")
		sys.stdout.flush()
		sum = computeSum(f)
		if sum not in self.dbDict:
			self.dbDict[sum]=[]
		if f not in self.dbDict[sum]:
			self.dbDict[sum].append(f)
		print("done")

	def saveDb(self):
		pickle.dump(self.dbDict, open(self.db, "wb"))

	def loadDb(self, db=None):
		self.dbDict = pickle.load(open(self.db, "rb"))
		return self.dbDict

	def updateDict(self, d, opts):
		l=[]
		for sum, x in d.items():
			for y in x:
				if y in opts:
					x.remove(y)
				if len(x)==0:
					l.append(sum)
					break
		for sum in l:
			del(d[sum])

		pickle.dump(d, open( self.db, "wb" ) )

	def main(self, stdscr):
		d=self.dbDict

		if self.all:
			l = [ x for x in filter(lambda x: x!=0, d) ]
		else:
			l = [ x for x in filter(lambda x: x!=0 and len(d[x])>1, d) ]
		ll=[]
		for x in l:
			ll .append(d[x].copy())

		pikr = Picker(
			title   = 'duplicate media manager'
		,	options = ll
		,	log     = self.log
		)

		while 1:
			pikr.run()
			removed = pikr.getRemoved()
			if removed:
				self.updateDict(d, removed)

				print ("hit a key to continue ... ")
				c = sys.stdin.read(1)

			if pikr.aborted:
				break


dm=DupManager(sys.argv)
if not dm.test:
	wrapper(lambda stdscr: dm.main(stdscr))

