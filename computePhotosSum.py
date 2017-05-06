#!/bin/python3
import psycopg2
import pickle
import sys, os
import exiftool


import hashlib

def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
	for block in bytesiter:
		hasher.update(block)
	return (hasher.hexdigest() if ashexstr else hasher.digest())

def file_as_blockiter(afile, blocksize=65536):
	with afile:
		block = afile.read(blocksize)
		while len(block) > 0:
			yield block
			block = afile.read(blocksize)

import binascii
def byteToHex(data):
	return str(binascii.b2a_hex(data), 'utf-8')

def connect():
	conn = psycopg2.connect("dbname=photo user=postgres")
	conn.set_client_encoding('utf-8')
	cur = conn.cursor()
	return cur

def getPhotos(nb):
	cur = connect()
	cur.execute("SELECT path FROM photo_image LIMIT %d" %nb)
	return cur.fetchall()

def getPhotoByName(path, name):
	cur = connect()
	cur.execute(
		"SELECT path,name FROM photo_image WHERE path LIKE '%path' AND upper(name) LIKE upper('%name') ORDER BY random() LIMIT 1" %(path, name)
	); 
	return cur.fetchall()

def computeSum(n):
	l=getPhotos(n)
	d={}
	i=0
	# this is in order to collect also some metadata using get_metadata
	# but this is a bit heavy
	#et = exiftool.ExifTool()
	#et.start()
	for fnamel in l:
		if (i%1000==0):
			sys.stdout.write(".")
			sys.stdout.flush()
		i+=1
		fname = fnamel[0]
		if os.path.exists(fname):
			sum =  hash_bytestr_iter(file_as_blockiter(open(fname, 'rb')), hashlib.sha256())
			if sum in d:
				d[sum].append(fname)
				print ("detect dup filename", d[sum] )
			else:
				d[sum ] = [ fname ]
		else:
			if 0 in d:
				d[0].append(fname)
				print ("file not found", fname )
			else:
				d[0]=[fname]
	#et.terminate()
	return d

db = None
save = load = inline = False

for x in sys.argv[1:]:
	if x == "-s":
		save = True
	elif x == "-l":
		load = True
	elif x == "-i":
		inline = True
	else:
		db = x

if save and not load:
	d=computeSum(100000)
	pickle.dump( d, open( db, "wb" ) )
elif load:
	d=pickle.load(open( db, "rb" ) )
	l = [ x for x in filter(lambda x: len(d[x])>1, d) ]
	for x in l:
		if inline:
			l = [ "%s" %y for y in d[x] ]
			#l = [ "%s" %y for y in d[x] if f(y) and os.path.exists(y) ]
			if len(l)<=1: continue
			print( "|".join( l ) )
		else:
			l = [ "%s" %y for y in d[x] ]
			if len(l)<=1: continue
			for y in l:
				print ("%s" %y)
			print ("")
else:
	print ("usage: [-l|-s] [-i] db.pickle,  load/save a pickle database")
