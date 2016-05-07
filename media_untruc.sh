#!/bin/sh

# patch might need to be applied to netpbm sources :
# diff -ru netpbm/pnm/pnmtojpeg.c netpbm-free-10.0/pnm/pnmtojpeg.c
# --- netpbm/pnm/pnmtojpeg.c      2003-08-12 20:23:03.000000000 +0200
# +++ netpbm-free-10.0/pnm/pnmtojpeg.c    2014-07-07 21:35:52.937573381 +0200
# @@ -426,7 +426,7 @@
#     but don't recognize any error either.
#  -----------------------------------------------------------------------------*/
#      FILE * exif_file;
# -    short length;
# +    unsigned short length;
# 
#      exif_file = pm_openr(exif_filespec);

untrunc_jpeg() {
 if [ ! -f "$1" ]; then
  echo "$1" read failure $?
  return
 fi
 jpegtopnm -exif=/tmp/img.exif "$1" > /tmp/img.pnm 2>&1 
 jpegtopnm "$1" > /tmp/img.pnm 2> /tmp/img.errors
 egrep -sq "(Corrupt|Premature)" /tmp/img.errors
 if [ $? -ne 0 ]; then
  echo "$1" ok
  rm /tmp/img.pnm /tmp/img.exif
  return
 fi
 echo "$1" corrupt
 pnmcrop -sides /tmp/img.pnm > /tmp/img.crop.pnm
# nikon d700 quality
# jpeg fine: 98/99
 pnmtojpeg --exif=/tmp/img.exif --quality=98 --optimize --dct=float /tmp/img.crop.pnm > "${1%.JPG}.fixed.jpg"
 rm /tmp/img.crop.pnm
}

while [ $# -ne 0 ]; do
 untrunc_jpeg "$1";
 shift
done
