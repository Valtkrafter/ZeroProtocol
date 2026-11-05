#!/bin/sh
# Yoru - NEW SPRINT, round 4: preview frames of r4 P2 (r3 P2 is reused from frames_r3, same settings).   sh build_sprint_r4_renderall.sh
# Rows: game camera (1080p size, every 2nd frame), game camera zoomed (60 fps), side in place (60 fps).
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
R="C:/Users/valen/ZeroProtocol/Blender"
S="$R/scripts/build_sprint_r1_render.py"
F="$R/work/Sprint/frames_r4"
EVEN=$(seq -s, 0 2 106)
BL="$R/work/Sprint/Yoru_Sprint_r4.blend"; AC="Yoru_Sprint_r4_P2"; GJ="$R/work/Sprint/Yoru_Sprint_r4_gait.json"
"$B" -b --factory-startup "$BL" --python "$S" -- "$F/P2_wide" "$GJ" view=game action=$AC frames=$EVEN res=1920x1080 crop=wide 2>&1 | grep -E "RENDER DONE|Error|Traceback"
"$B" -b --factory-startup "$BL" --python "$S" -- "$F/P2_body" "$GJ" view=game action=$AC frames=0-107 res=6400x3600 crop=body 2>&1 | grep -E "RENDER DONE|Error|Traceback"
"$B" -b --factory-startup "$BL" --python "$S" -- "$F/P2_side" "$GJ" view=side action=$AC frames=0-35 res=330x440 2>&1 | grep -E "RENDER DONE|Error|Traceback"
echo ALL RENDERS DONE
