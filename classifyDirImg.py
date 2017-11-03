#!/bin/python3

import sys, pdb
import os, re
from classifyImg import classifyImg

src=sys.argv[1]
#target=sys.argv[2]

def parsedir(d):
	for root, subfolder, files in os.walk(d):
		for file in files:
			fullname="%s/%s" %(root, file)
			if fullname.find("@eaDir/")==-1 and fullname.find(".DS_Store") == -1:
				yield fullname


if __name__ == "__main__":
	test = "-test" in sys.argv[1:]
	if os.path.isfile(src):
		print (classifyImg(src, testOnly=test))
	elif os.path.isdir(src):
		for x in parsedir(src):
			print(classifyImg(x, testOnly=test))
	else:
		print("do not exist")
