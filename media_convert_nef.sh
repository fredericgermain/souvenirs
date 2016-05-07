#!/bin/sh

DENOISE_OPTION="-n 1000"
DENOISE_OPTION="-n 500"
OPTIONS="-W -w -q 3 -m 2 $DENOISE_OPTION"

set -x
conv() {
  IN_FILE=$1
  OUT_FILE=$(basename "$IN_FILE" ".nef").dcraw.jpg
  dcraw -c $OPTIONS "$IN_FILE" | cjpeg -quality 100 -optimize -progressive > $OUT_FILE
  exiftool -tagsFromFile "$IN_FILE" "$OUT_FILE"
  rm "${OUT_FILE}_original"
}

conv $1
