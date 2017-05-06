from subprocess import call, run, PIPE
import datetime
import struct
import sys, os
import re, shutil

photoBaseDir="/media/photo"

ATOM_HEADER_SIZE = 8
# difference between Unix epoch and QuickTime epoch, in seconds
EPOCH_ADJUSTER = 2082844800

datePatStr = "(?P<y>[0-9]{4}):(?P<m>[0-9]{2}):(?P<d>[0-9]{2}) (?P<h>[0-9]{2}):(?P<mn>[0-9]{2}):(?P<s>[0-9]{2})"
datePat = re.compile(datePatStr)
filePat = re.compile("(.*/|^)IMG_(?P<y>[0-9]{4})(?P<m>[0-9]{2})(?P<d>[0-9]{2})_(?P<h>[0-9]{2})(?P<mn>[0-9]{2})(?P<s>[0-9]{2})\..*")
exifPat = re.compile("Create Date[^:]+: (?P<date>%s).*" %datePatStr)

def timeFromFileName(filename):
	ret=filePat.match(filename)
	if ret:
		res="%s:%s:%s %s:%s:%s" %(ret.group('y'), ret.group('m'), ret.group('d'), ret.group('h'), ret.group('mn'), ret.group('s'))
	else:
		res=''
	return res

def getYearMonth(datestr):
	ret=datePat.match(datestr)
	return ret.group('y'), ret.group('m')

def movTime(filename):
	# open file and search for moov item
	f = open(filename, "rb")
	while 1:
		atom_header = f.read(ATOM_HEADER_SIZE)
		if atom_header[4:8].decode('ascii') == 'moov':
			break
		else:
			if atom_header == b'':
				print("ERROR: moov not found, something wrong happen")
				return timeFromFileName(filename)
			atom_size = struct.unpack(">I", atom_header[0:4])[0]
			f.seek(atom_size - 8, 1)
	
	# found 'moov', look for 'mvhd' and timestamps
	atom_header = f.read(ATOM_HEADER_SIZE)
	if atom_header[4:8].decode('ascii') == 'cmov':
		print("ERROR: mov atom is compressed")
		s=timeFromFileName(filename)
	elif atom_header[4:8].decode('ascii') != 'mvhd':
		print("ERROR: expected to find 'mvhd' header got %s" %atom_header[4:8].decode('ascii'))
		s=timeFromFileName(filename)
	else:
		f.seek(4, 1)
		creation_date = struct.unpack(">I", f.read(4))[0]
		modification_date = struct.unpack(">I", f.read(4))[0]
		# print "creation date:",
		s="%s" %datetime.datetime.utcfromtimestamp(creation_date - EPOCH_ADJUSTER)
		s=s.replace("-",":")
	return s

def videoTime(filename):
	res = run(['/bin/exiftool', '-CreateDate', filename], stdout=PIPE, stderr=PIPE)
	res=res.stdout.decode('ascii').strip()
	if res:
		ret = exifPat.match(res)
		if ret:
			res = ret.group("date")
		else:
			ret = ""
	else:
		res = timeFromFileName(filename)
	return res

def imgTime(filename):
	res=run(['/bin/exiv2', '-g', 'Exif.Image.DateTime', '-Pv', filename], stdout=PIPE, stderr=PIPE)
	res=res.stdout.decode('ascii').strip()
	if not res:
		res=run(['/bin/exiv2', '-g', 'DateTimeOriginal', '-Pv', filename], stdout=PIPE, stderr=PIPE)
		res=res.stdout.decode('ascii').strip()
	if not res:
		res = timeFromFileName(filename)
	return res

def getDestDirName(datestr):
	ret=datePat.match(datestr)
	return "%s/%s" %(ret.group('y'), ret.group('m'))

def getTimeFromDateFile(filename):
	return datetime.datetime.fromtimestamp(int(os.path.getctime(filename))).strftime('%Y:%m:%d %H:%M:%S')

def mediaTime(filename):
	ext = filename[-3:]
	if ext.lower() in [ "jpg", "png", "gif" ]:
		ret = imgTime(filename)
	elif ext.lower() == "mov":
		ret = videoTime(filename)
		if not ret:
			ret=movTime(filename)
	elif ext.lower() == "mp4":
		ret = videoTime(filename)
	else:
		ret = ""
	if ret:
		y,m = getYearMonth(ret)
		if y=='0000':
			ret = ""
	if not ret:
		ret=getTimeFromDateFile(filename)
	return ret

def move(src, dest):
	shutil.move(src, dest)
	#shutil.copy2(src, dest)
	#os.remove(src)

def safeMove(src, dest):
	if os.path.exists(dest):
		ret=call(["diff", "-q", src, dest])
		if not ret:
			move(src, dest)
		else:
			file, ext = os.path.splitext(dest)
			i = 1
			newdest = lambda x : file + "_" + str(x) + ext
			while os.path.exists(newdest(i)):
				ret=call(["diff", "-q", src, newdest(i)])
				if not ret:
					break
				i+=1
			move(src, file + "_" + str(i) + ext)
	else:
		move(src, dest)

def classifyImg(filename, dir=".", testOnly=False):
	bname = os.path.basename(filename)
	t = mediaTime(filename)
	msg=[]
	if t:
		dname = "%s/%s/%s" %(photoBaseDir, dir, getDestDirName(t))
		if not os.path.exists(dname):
			if not testOnly:
				os.makedirs(dname)
			msg.append("\tos.makedirs(%s)" %dname)
		destfile = "%s/%s" %(dname, bname)
		msg.append("\tmv %s %s" %(filename, destfile))
		if not testOnly:
			safeMove(filename, destfile)
	else:
		msg.append("\tunable to compute date, skip file %s" %filename)
	return "\n\t".join(msg)

if __name__ == "__main__":
	print(classifyImg(sys.argv[1]))
