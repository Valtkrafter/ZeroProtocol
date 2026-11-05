#!/bin/sh
# Yoru - NEW SPRINT, round 5: preview frames of r5 P2 (game camera normal and zoomed, side view larger) and the larger side view of r4 P2.
#   sh build_sprint_r5_renderall.sh
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
R="C:/Users/valen/ZeroProtocol/Blender"
S="$R/scripts/build_sprint_r1_render.py"
F="$R/work/Sprint/frames_r5"
EVEN=$(seq -s, 0 2 106)
BL="$R/work/Sprint/Yoru_Sprint_r5.blend"; GJ="$R/work/Sprint/Yoru_Sprint_r5_gait.json"
"$B" -b --factory-startup "$BL" --python "$S" -- "$F/R5_wide" "$GJ" view=game action=Yoru_Sprint_r5_P2 frames=$EVEN res=1920x1080 crop=wide 2>&1 | grep -E "RENDER DONE|Error|Traceback"
"$B" -b --factory-startup "$BL" --python "$S" -- "$F/R5_body" "$GJ" view=game action=Yoru_Sprint_r5_P2 frames=0-107 res=6400x3600 crop=body 2>&1 | grep -E "RENDER DONE|Error|Traceback"
"$B" -b --factory-startup "$BL" --python "$S" -- "$F/R5_side" "$GJ" view=side action=Yoru_Sprint_r5_P2 frames=0-35 res=480x640 2>&1 | grep -E "RENDER DONE|Error|Traceback"
"$B" -b --factory-startup "$BL" --python "$S" -- "$F/R4_side" "$GJ" view=side action=Yoru_Sprint_r4_P2 frames=0-35 res=480x640 2>&1 | grep -E "RENDER DONE|Error|Traceback"
echo ALL RENDERS DONE
