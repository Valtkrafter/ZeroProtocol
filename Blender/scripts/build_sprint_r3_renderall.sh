#!/bin/sh
# Yoru - NEW SPRINT, round 3: all preview frames (Git Bash).  Columns P1 / P2 (ALT is reused from frames_r2, same settings); plus 6 back frames at 3840 for the NTE comparison.
#   sh build_sprint_r3_renderall.sh            (or: COLS="P1" sh build_sprint_r3_renderall.sh)
# Rows: game camera (1080p size, every 2nd frame = 30 fps), game camera zoomed (60 fps), side in place (60 fps), front close-up (60 fps).
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
R="C:/Users/valen/ZeroProtocol/Blender"
S="$R/scripts/build_sprint_r1_render.py"
F="$R/work/Sprint/frames_r3"
EVEN=$(seq -s, 0 2 106)
for col in ${COLS:-P1 P2}; do
  if [ "$col" = "ALT" ]; then BL="$R/Yoru_Run.blend"; AC="Yoru_Run"; GJ="$R/Yoru_Run_gait.json";
  else BL="$R/work/Sprint/Yoru_Sprint_r3.blend"; AC="Yoru_Sprint_r3_$col"; GJ="$R/work/Sprint/Yoru_Sprint_r3_gait.json"; fi
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_wide" "$GJ" view=game action=$AC frames=$EVEN res=1920x1080 crop=wide 2>&1 | grep -E "RENDER DONE|Error|Traceback"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_body" "$GJ" view=game action=$AC frames=0-107 res=6400x3600 crop=body 2>&1 | grep -E "RENDER DONE|Error|Traceback"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_side" "$GJ" view=side action=$AC frames=0-35 res=330x440 2>&1 | grep -E "RENDER DONE|Error|Traceback"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_front" "$GJ" view=front action=$AC frames=0-35 res=300x384 2>&1 | grep -E "RENDER DONE|Error|Traceback"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/${col}_back" "$GJ" view=game action=$AC frames=0,6,12,18,24,30 res=3840x2160 crop=wide 2>&1 | grep -E "RENDER DONE|Error|Traceback"
done
echo ALL RENDERS DONE
