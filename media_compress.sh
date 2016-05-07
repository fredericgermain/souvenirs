#!/bin/sh

WORKDIR=$HOME
[ -d $WORKDIR ] || mkdir -p $WORKDIR

compress_video() {
  #  transcode -i 20140801_230943.mp4 -Z 720x576 -y xvid -o 20140801_230943.small.mp4


  # iphone4 640x960
  # galaxy S 480x800
  i=$1
  prettyname=${i%.avi}
  echo processing $prettyname
  dir=$(dirname "$prettyname")
  mkdir -p "$WORKDIR/$dir"
  mencoder "$i" \
	 -o "$WORKDIR/$prettyname.menc.avi" \
	-vf scale=-10:480,harddup \
	-ovc xvid -xvidencopts bitrate=800 \
	-oac copy \
	-sub "$prettyname.srt" -font arial.ttf -subfont-text-scale 4

	#-srate 48000 \
	#-oac faac -faacopts mpeg=4:object=2:br=96 \

  ffmpeg -i "$WORKDIR/$prettyname.menc.avi"  -vcodec mpeg4  -ac 2 -ar 44100 -ab 128000 "$WORKDIR/$prettyname.mp4"
  #ffmpeg -i "$WORKDIR/$prettyname.menc.avi"  -vcodec mpeg4 -acodec copy "$WORKDIR/$prettyname.mp4"
  rm "$WORKDIR/$prettyname.menc.avi"	
}

notes() {
#-ovc x264 -x264encopts nocabac:level_idc=30:bframes=0 \
#-oac faac -faacopts mpeg=4:object=2:raw:br=128 \
#-of lavf -lavfopts format=mp4 \
#droid
#-ovc x264 -x264encopts bitrate=640:nocabac:direct_pred=auto:me=umh:frameref=2:level_idc=21:partitions=all:subq=6:threads=auto:trellis=1:vbv_maxrate=768:vbv_bufsize=244:bframes=0 \
echo mplayer "$WORKDIR/$prettyname.menc.avi" -dumpaudio -dumpfile "$WORKDIR/$prettyname.aac"
echo mplayer "$WORKDIR/$prettyname.menc.avi" -dumpvideo -dumpfile "$WORKDIR/$prettyname.mp4v"
mp4creator -create="$WORKDIR/$prettyname.aac" "$WORKDIR/$prettyname.mp4"
mp4creator -create="$WORKDIR/$prettyname.mp4v" -rate=23.976 "$WORKDIR/$prettyname.mp4"
mp4creator -hint=1 "$WORKDIR/$prettyname.mp4"
mp4creator -hint=2 "$WORKDIR/$prettyname.mp4"
mp4creator -optimize "$WORKDIR/$prettyname.mp4"
mp4creator -list "$WORKDIR/$prettyname.mp4"
rm "$WORKDIR/$prettyname.avi"
rm "$WORKDIR/$prettyname.h264"
rm "$WORKDIR/$prettyname.aac"
}

compress_wav() {
  WAVFILE=$1
  OGGFILE=${1%wav}ogg

  oggenc -q7 "$WAVFILE"
  touch -r "$WAVFILE" "$OGGFILE"
}

if [ "$1" != "${1%wav}" ]; then
	compress_wav "$1"
fi

