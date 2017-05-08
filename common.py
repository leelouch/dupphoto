import os
import hashlib
import sys, os
import binascii

def parseDir(d, excludeFunc=None):
	for root, subfolder, files in os.walk(d):
		for file in files:
			fullname="%s/%s" %(root, file)
			if excludeFunc(fullname):
				continue
			yield fullname

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

def byteToHex(data):
	return str(binascii.b2a_hex(data), 'utf-8')

def connect():
	import psycopg2
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

def computeSum(fname):
	return hash_bytestr_iter(file_as_blockiter(open(fname, 'rb')), hashlib.sha256())

