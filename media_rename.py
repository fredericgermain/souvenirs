#!/usr/bin/python
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime, timedelta, tzinfo
import os
import sys
import struct
import time
import traceback
import math

# for JS style coding 
# http://stackoverflow.com/questions/2827623/python-create-object-and-add-attributes-to-it
class Object(object):
    pass

# a quick UTC timezone class
# http://stackoverflow.com/questions/2331592/datetime-datetime-utcnow-why-no-tzinfo
ZERO = timedelta(0)

# A UTC class.

class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

class MovInfo(object):
    # from http://stackoverflow.com/questions/21355316/getting-metadata-for-mov-video/21395803#21395803
    ATOM_HEADER_SIZE = 8
    # difference between Unix epoch and QuickTime epoch, in seconds
    EPOCH_ADJUSTER = 2082844800

    def __init__(self, filename):
        self.filename = filename
        self.parse_depth = 0

    def parse(self):
        # open file and search for moov item
        f = open(self.filename, "rb")
    
        self.tracks = []

        byte_read = self.parse_atom_list(f, -1)

        f.close()
    
    def parse_atom_list(self, f, max_size):
        bytes_read = 0
        self.parse_depth = self.parse_depth + 1
        
        while max_size == -1 or bytes_read < max_size:
            atom_header = f.read(MovInfo.ATOM_HEADER_SIZE)
            if len(atom_header) == 0:
                #reached end of file
                break
                
            atom_id = atom_header[4:8]
            atom_size = struct.unpack(">I", atom_header[0:4])[0]
            tabs = ''.ljust(2*(self.parse_depth-1))
            print "%satom %s @:%d size:%d" % (tabs, atom_id, f.tell() - MovInfo.ATOM_HEADER_SIZE, atom_size)

            atom_bytes_read = 0
            if atom_id == 'ftyp':
                atom_bytes_read = self.parse_ftyp(f, atom_size)
            elif atom_id == 'moov':
                atom_bytes_read = self.parse_moov(f, atom_size)
            elif atom_id == 'stsd':
                version, flag0, flag1, flag2, nb = struct.unpack(">BBBBI", f.read(8))
                atom_bytes_read = 8
                atom_bytes_read = 8 + self.parse_atom_list(f, atom_size - MovInfo.ATOM_HEADER_SIZE - 8)
            elif atom_id == 'stts':
                version, flag0, flag1, flag2, nb = struct.unpack(">BBBBI", f.read(8))
                stts = []
                i = 0
                if 16 + nb * 8 != atom_size:
                    raise "bad"
                while i < nb:
                    frame_count, frame_duration = struct.unpack(">II", f.read(8))
                    stts.append((frame_count, frame_duration))
                    i = i + 1

                self.current_track['stts'] = stts
                atom_bytes_read = atom_size - MovInfo.ATOM_HEADER_SIZE

            elif atom_id == 'stsc':
                version, flag0, flag1, flag2, nb = struct.unpack(">BBBBI", f.read(8))
                stsc = []
                i = 0
                if 16 + nb * 12 != atom_size:
                    raise "bad"
                while i < nb:
                    frame_count, frame_duration, z = struct.unpack(">III", f.read(12))
                    stsc.append((frame_count, frame_duration, z))
                    i = i + 1

                self.current_track['stsc'] = stsc
                atom_bytes_read = atom_size - MovInfo.ATOM_HEADER_SIZE

            elif atom_id == 'stsz':
                version, flag0, flag1, flag2, block_size, nb = struct.unpack(">BBBBII", f.read(12))
                
                if block_size == 0:
                    if 20 + nb * 4 != atom_size:
                        raise "bad"
                    stsz = []
                    i = 0
                    while i < nb:
                        frame_size = struct.unpack(">I", f.read(4))
                        stsz.append(frame_size)
                        i = i + 1
                else:
                    stsz = nb

                self.current_track['stsz'] = stsz
                atom_bytes_read = atom_size - MovInfo.ATOM_HEADER_SIZE

            elif atom_id == 'stco':
                version, flag0, flag1, flag2, nb = struct.unpack(">BBBBI", f.read(8))
                
                if 16 + nb * 4 != atom_size:
                    raise "bad"
                stco = []
                i = 0
                while i < nb:
                    frame_offset = struct.unpack(">I", f.read(4))
                    stco.append(frame_offset)
                    i = i + 1
                
                self.current_track['stco'] = stco
                atom_bytes_read = atom_size - MovInfo.ATOM_HEADER_SIZE


            elif atom_id == 'ctts':
                version, flag0, flag1, flag2, nb = struct.unpack(">BBBBI", f.read(8))
                
                print nb
                if 16 + nb * 8 != atom_size:
                    raise "bad"
                ctts = []
                i = 0
                while i < nb:
                    frame_offset = struct.unpack(">II", f.read(8))
                    ctts.append(frame_offset)
                    i = i + 1
                
                self.current_track['ctts'] = ctts
                atom_bytes_read = atom_size - MovInfo.ATOM_HEADER_SIZE


            elif atom_id == 'stss':
                version, flag0, flag1, flag2, nb = struct.unpack(">BBBBI", f.read(8))
                
                print nb, atom_size
                if 16 + nb * 4 != atom_size:
                    raise "bad"
                stss = []
                i = 0
                while i < nb:
                    frame_offset = struct.unpack(">I", f.read(4))
                    stss.append(frame_offset)
                    i = i + 1
                
                self.current_track['stss'] = stss
                atom_bytes_read = atom_size - MovInfo.ATOM_HEADER_SIZE

            elif atom_id in ('trak', 'edts', 'mdia', 'minf', 'dinf', 'stbl', 'udta', 'NCDT'):
                if atom_id == 'trak':
                    self.current_track = {}
                    self.tracks.append(self.current_track)
                atom_bytes_read = self.parse_atom_list(f, atom_size - MovInfo.ATOM_HEADER_SIZE)

            f.seek(atom_size - MovInfo.ATOM_HEADER_SIZE - atom_bytes_read, 1)
            
            bytes_read = bytes_read + atom_size

        self.parse_depth = self.parse_depth - 1
        return bytes_read

    def parse_ftyp(self, f, atom_size):
        self.ftyp = {}

        data = f.read(8)
        self.ftyp['major_brand'] = data[0:4]
        self.ftyp['major_brand_version'] = struct.unpack(">I", data[4:8])[0]
        atom_bytes_read = 8
        
        self.ftyp['compatible_brands'] = []
        while MovInfo.ATOM_HEADER_SIZE + atom_bytes_read < atom_size:
            data = f.read(4)
            self.ftyp['compatible_brands'].append(data[0:4])
            atom_bytes_read = atom_bytes_read + 4

        return atom_bytes_read

    def parse_moov(self, f, moov_size):
        # found 'moov', look for 'mvhd' and timestamps
        atom_header = f.read(MovInfo.ATOM_HEADER_SIZE)
        if len(atom_header) == 0:
            raise 'reached end of file'

        atom_id = atom_header[4:8]
        atom_size = struct.unpack(">I", atom_header[0:4])[0]
        bytes_read = 0
        if atom_id == 'cmov':
            print "moov atom is compressed"
        elif atom_id == 'mvhd':
            mvhd = {}
            
            version, flag0, flag1, flag2 = struct.unpack(">BBBB", f.read(4))

            if version == 0:
                mvhd['creation_date'], mvhd['modification_date'], mvhd['timescale'], mvhd['duration'], mvhd['language'], mvhd['quality'] = struct.unpack(">IIIIHH", f.read(4*4 + 2*2))

            self.mvhd = mvhd
            
            f.seek(atom_size - (MovInfo.ATOM_HEADER_SIZE + 6 * 4), 1)
            bytes_read = atom_size - MovInfo.ATOM_HEADER_SIZE

            bytes_read = bytes_read + self.parse_atom_list(f, moov_size - MovInfo.ATOM_HEADER_SIZE - atom_size) 
        else:
            print "expected to find 'mvhd' header"

        return MovInfo.ATOM_HEADER_SIZE + bytes_read
    
    def __repr__(self):
        return json.dumps({ 'ftyp': self.ftyp, 'moov': { 'mvhd': self.mvhd}, 'tracks': self.tracks}, indent=4)

class MediaInfo(object):
    """ The MediaInfo object contains info for a media that can be
        used to rename
        
        Example:
            infos = MediaInfo("video.mkv")"""

    def __init__(self, filename):
        self.filename = filename

    def fetch_exif(self):
        ret = {}
        i = Image.open(self.filename)
        info = i._getexif()
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            ret[decoded] = value
        return ret

    def get_exif(self):
        if not hasattr(self, "exif"):
            self.exif = self.fetch_exif()
        return self.exif

    def get_pil_create_date(self):
        exif = get_exif()
        self.exif_ctime = datetime.strptime(exif["DateTimeOriginal"], '%Y:%m:%d %H:%M:%S')
        return self.exif_ctime

    def get_mov_create_date(self):
        if not hasattr(self, "mov"):
            self.mov = MovInfo(self.filename)
            self.mov.parse()

        print self.mov

        if 'niko' in self.mov.ftyp['compatible_brands']:
            # nikon camera store qt time adding local offset
            epoch_in_utc = True 
            creation_date_is_end_of_recording = False
        else:
            epoch_in_utc = False
            creation_date_is_end_of_recording = True

        if epoch_in_utc:
            tz = UTC()
            # better to use utc date
            #modification_date = self.mov.modification_date - MovInfo.EPOCH_ADJUSTER + time.timezone
        else:
            print "WARNING: using current computer timezone to interpret creation date"
            tz = None

        creation_date = self.mov.mvhd['creation_date'] - MovInfo.EPOCH_ADJUSTER
        modification_date = self.mov.mvhd['modification_date'] - MovInfo.EPOCH_ADJUSTER
#        print "creation date: %d, %s" % (creation_date, datetime.fromtimestamp(creation_date, tz))
#       print "modification date: %d, %s" % (modification_date, datetime.fromtimestamp(modification_date, tz))
        #self.ctime = datetime.utcfromtimestamp(creation_date)
        if creation_date_is_end_of_recording:

            duration_seconds = math.ceil(1.0*self.mov.mvhd['duration']/self.mov.mvhd['timescale'])
            print duration_seconds
            # remove 1s (duration to write header ?) from creation date to be synced with Nexus filename
            creation_date = creation_date - duration_seconds - 1
        
        ctime = datetime.fromtimestamp(creation_date, tz)

        return ctime

    def get_wav_create_date(self):
        # valid for wav file recorded 
        if not hasattr(self, "wav"):
            import wave
            self.wav = wave.open(self.filename, 'r')

        duration = self.wav.getnframes() / self.wav.getframerate();
        mtime = os.path.getmtime(self.filename)
        
        return datetime.fromtimestamp(mtime - duration - 1)

    def get_ogg_create_date(self): 
        if not hasattr(self, "ogg"):
            import kaa.metadata
            self.ogg = kaa.metadata.parse(self.filename)
        
        duration = self.ogg.length
        mtime = os.path.getmtime(self.filename)
        
        return datetime.fromtimestamp(mtime - duration - 1)

    def get_pyexiv2_create_date(self):        
        if not hasattr(self, "pyexiv2_metadata"):
            import pyexiv2
            try:
                pyexiv2_metadata = pyexiv2.ImageMetadata(self.filename)
                pyexiv2_metadata.read()
                self.pyexiv2_metadata = pyexiv2_metadata
            except IOError:
                raise IOError("%s not supported by pyexiv2" % (self.filename))
        else:
            pyexiv2_metadata = self.pyexiv2_metadata

        #for k in pyexiv2_metadata.iterkeys():
            #print "%s -> %s" % (k, pyexiv2_metadata[k])
            #print "%s -> %s" % (k, pyexiv2_metadata.exif_keys[k])
         
    #    print pyexiv2_metadata.iptc_keys
    #    print pyexiv2_metadata.xmp_keys
    #    print metadata["Exif.Photo.DateTimeOriginal"]
        try:
            self.exif_ctime = datetime.strptime(pyexiv2_metadata["Exif.Photo.DateTimeOriginal"].raw_value, '%Y:%m:%d %H:%M:%S')
        except KeyError, err:
            try:
                # nexus 5 front camera do no embed DateTimeOriginal...
                utc_ctime = datetime.strptime("%s %s" % (
                    pyexiv2_metadata["Exif.GPSInfo.GPSDateStamp"].raw_value,
                    pyexiv2_metadata["Exif.GPSInfo.GPSTimeStamp"].raw_value
                    ), '%Y:%m:%d %H/1 %M/1 %S/1').replace(tzinfo=UTC())

                import calendar
                print calendar.timegm(utc_ctime.timetuple())
                self.exif_ctime = datetime.fromtimestamp(calendar.timegm(utc_ctime.timetuple()))
                print self.exif_ctime
            except KeyError, err:
                print err
                raise IOError("%s no tag" % (self.filename))

        return self.exif_ctime

    def get_create_date(self):
        try:
            filenameu = self.filename.upper()
            if filenameu.endswith(".JPG"):
                return self.get_pyexiv2_create_date()
            elif filenameu.endswith(".NEF"): # NIKON RAW
                return self.get_pyexiv2_create_date()
            elif filenameu.endswith(".MOV"):
                return self.get_mov_create_date()
            elif filenameu.endswith(".MP4"):
                return self.get_mov_create_date()
            elif filenameu.endswith(".WAV"):
                return self.get_wav_create_date()
            elif filenameu.endswith(".OGG"):
                return self.get_ogg_create_date()
            else:
                raise "file not handled"
        except Exception, err:
            import traceback
            print  traceback.format_exc()
            if os.path.isfile(self.filename):
                ctime = datetime.fromtimestamp(os.path.getctime(self.filename))
                print "metadata not found, using create date for %s => %s" % (self.filename, ctime)
                return ctime
        raise Exception("not a file")

    def match_device(self, devices):
        if hasattr(self, 'pyexiv2_metadata'):
            tags_name = 'pyexiv2'
        else:
            return None

        for d in devices:
            matched = False
            tags = d['tags'][tags_name]

            print tags
            try:
                if tags:
                    matched = True
                    for t in tags.keys():
                        if tags[t] != self.pyexiv2_metadata[t.encode('ascii')].raw_value:
    #                        print "bad %s %s %s" % (t, tags[t], self.pyexiv2_metadata[t.encode('ascii')].raw_value)
                            matched = False
                            break
            except:
                matched = False
            if matched:
                return d

        print self
        raise Exception("no device found for %s" % (self.filename))

        return None


    def __repr__(self):
        buffer = ""
        if hasattr(self, 'pyexiv2_metadata'):
            values = ""
            pyexiv2_metadata = self.pyexiv2_metadata
            buffer = "%s {" % ("exif")
            for k in pyexiv2_metadata.iterkeys():
                buffer += "%s: %s,\n" % (k, pyexiv2_metadata[k])
            buffer += "}"
        else:
            buffer += "??"
        return buffer


try:
    import json
    f = open(os.path.expanduser('~/.media_rename.json'))
    rename_conf = json.load(f)
    f.close()
except Exception, e:
    print e
    rename_conf = {}
    rename_conf['devices'] = []


def get_path_from_date(date_object):
    if date_object.hour < 5:
        date_object = date_object - timedelta(1) # minus one day

    return "%d-%02d-%02d" %(date_object.year, date_object.month, date_object.day)

def media_basename(cdate, device, id, ext):
    basename = "%04d%02d%02d_%02d%02d%02d"%  (
            cdate.year, cdate.month, cdate.day, 
            cdate.hour, cdate.minute, cdate.second )

    if device:
        basename += "_%s" % (device['id'])

    if id:
        basename += "_%s" % (id)

    basename += ".%s" % (ext)

    return basename


import glob
import re
def move_to_dir(filename):
    global dummy
    info = MediaInfo(filename)
    cdate = info.get_create_date()
    dest_dir_prefix = get_path_from_date(cdate)

    device = info.match_device(rename_conf['devices'])

    ext = re.sub('.*\.', '', filename).lower()
    basename = media_basename(cdate, device, None, ext)
#    basename = os.path.basename(filename)

    dirs = glob.glob("%s*" % (dest_dir_prefix))
    if len(dirs) == 1 and dirs[0] != dest_dir_prefix:
        dest_dir = dirs[0]
        dest_dir = dest_dir.decode('utf8')
        dir_choice_reason = " (only one choice)"
    else:
        dest_dir = dest_dir_prefix
        dir_choice_reason = ""      

    # avoid 
    dest_filename = os.path.join(dest_dir, basename)
    id_it = 0
    while os.path.isfile(dest_filename):
        if basename == os.path.basename(filename):
            if filename.startswith(dest_dir_prefix):
                print('%s already good directory' % (filename))
                return

        basename = media_basename(cdate, device, "%d" % id_it, ext)
        dest_filename = os.path.join(dest_dir, basename)
        id_it+=1

    print "%s -> %s/%s%s" % (filename.decode('utf8'), dest_dir, basename, dir_choice_reason )   
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)

    if not dummy: 
        os.rename(filename, dest_filename)

# in case we have files named like IMG_20160331_000230.jpg, IMG_20160331_000230_1.jpg IMG_20160331_000230_2.jpg ...,
# we want to start renaming with IMG_20160331_000230.
# we sort the list to do that, associating the key IMG_20160331_000230_0 with IMG_20160331_000230 like files
def file_key(filename):
    m = re.compile("(.*)IMG_([0-9]*)_([0-9]*)(.*).jpg").match(filename)
    if m is None:
        return filename
    g = m.groups()
    if g[3] == "":
        ret = "%sIMG_%s_%s_0.jpg" % (g[0], g[1], g[2])
    else:
        ret = filename
#    print "%s %s %s" % (filename, m.groups(), ret)
    return ret

argc_it = 1

dummy = False
if sys.argv[1] == "-d":
    dummy = True
    argc_it = argc_it + 1

file_list = sorted(sys.argv[argc_it:], key=file_key)

for path in file_list:
    move_to_dir(path)
