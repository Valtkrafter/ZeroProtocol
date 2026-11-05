#!/bin/sh
# Yoru - NEW SPRINT, round 1: all preview frames (Git Bash).  Columns ALT (old sprint, Blender/Yoru_Run.blend) and A / B / C.
#   sh build_sprint_r1_renderall.sh            (or: COLS="A B C" sh build_sprint_r1_renderall.sh  to render only some columns)
# Writes Blender/work/Sprint/frames/<col>_<row>/*.png ; then build_sprint_r1_media.py and build_sprint_r1_sheet.py make the video and sheets.
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
R="C:/Users/valen/ZeroProtocol/Blender"
S="$R/scripts/build_sprint_r1_render.py"
F="$R/work/Sprint/frames"
STEP3="0,3,6,9,12,15,18,21,24,27,30,33"
for col in ${COLS:-ALT A B C}; do
  if [ "$col" = "ALT" ]; then BL="$R/Yoru_Run.blend"; AC="Yoru_Run"; GJ="$R/Yoru_Run_gait.json";
  else BL="$R/work/Sprint/Yoru_Sprint_r1.blend"; AC="Yoru_Sprint_r1_$col"; GJ="$R/work/Sprint/Yoru_Sprint_r1_gait.json"; fi
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_wide" "$GJ" view=game action=$AC frames=0-107 res=1920x1080 crop=wide 2>&1 | grep -E "RENDER DONE|Error|Traceback"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_body" "$GJ" view=game action=$AC frames=0-107 res=8960x5040 crop=body 2>&1 | grep -E "RENDER DONE|Error|Traceback"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_front" "$GJ" view=front action=$AC frames=0-35 res=360x460 2>&1 | grep -E "RENDER DONE|Error|Traceback"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_back" "$GJ" view=game action=$AC frames=$STEP3 res=3840x2160 crop=wide 2>&1 | grep -E "RENDER DONE|Error|Traceback"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_side" "$GJ" view=side action=$AC frames=$STEP3 res=360x480 2>&1 | grep -E "RENDER DONE|Error|Traceback"
done
echo ALL RENDERS DONE
