#!/bin/sh
# Yoru - SPRINT LEAN CORRECTION r6: preview frames of R5 P2 (as baked) and the lean variants L20 / L23 / L26 from Yoru_Sprint_r6.blend:
# game camera (every 2nd frame, 1080p, crop=wide), game camera zoomed on arms / pistols / upper body (crop=body), side view 720 x 960 (r5: 480 x 640).
# The four columns render in parallel (one background Blender per column, its three rows one after the other).
#   sh build_sprint_r6_renderall.sh
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
R="C:/Users/valen/ZeroProtocol/Blender"
S="$R/scripts/build_sprint_r1_render.py"
F="$R/work/Sprint/frames_r6"
EVEN=$(seq -s, 0 2 106)
BL="$R/work/Sprint/Yoru_Sprint_r6.blend"; GJ="$R/work/Sprint/Yoru_Sprint_r6_gait.json"
column() {   # $1 = column name, $2 = action
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/$1_wide" "$GJ" view=game action=$2 frames=$EVEN res=1920x1080 crop=wide 2>&1 | grep -E "RENDER DONE|CROP|Error|Traceback" | sed "s/^/$1 /"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/$1_body" "$GJ" view=game action=$2 frames=0-107 res=6400x3600 crop=body 2>&1 | grep -E "RENDER DONE|CROP|Error|Traceback" | sed "s/^/$1 /"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/$1_side" "$GJ" view=side action=$2 frames=0-35 res=720x960 2>&1 | grep -E "RENDER DONE|Error|Traceback" | sed "s/^/$1 /"
}
column R5 Yoru_Sprint_r5_P2 &
column L20 Yoru_Sprint_r6_L20 &
column L23 Yoru_Sprint_r6_L23 &
column L26 Yoru_Sprint_r6_L26 &
wait
echo ALL RENDERS DONE
