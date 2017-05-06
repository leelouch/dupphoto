#!/usr/bin/python3

import curses
import pickle
import picker
import sys, os
import shutil
import argparse

from picker import Picker
from curses import wrapper

class DupManager(object):
	def __init__(self, argv):
		parser     = argparse.ArgumentParser()

		parser.add_argument('-all', action='store_true', help='load all db, do not filter dup only')
		parser.add_argument('-log', action='store_true', help='verbose to log file')
		parser.add_argument('db'  , type=str, nargs=1, help='db filename')

		argList = argv[1:]
		args=parser.parse_args(argList)
		if not argList:
			parser.error("")

		self.db = args.db[0]
		self.all= args.all
		self.log= args.log
		print (self.db, self.all, self.log)

	def updateDict(self, d, opts):
		l=[]
		for sum, x in d.items():
			for y in x:
				if y in opts:
					x.remove(y)
				if len(x)<=1:
					l.append(sum)
					break
		for sum in l:
			del(d[sum])
		pickle.dump(d, open( self.db, "wb" ) )

	def main(self, stdscr):
		d=pickle.load(open( self.db, "rb" ) )

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
wrapper(lambda stdscr: dm.main(stdscr))
