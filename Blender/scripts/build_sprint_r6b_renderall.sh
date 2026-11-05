#!/bin/sh
# Yoru - SPRINT LEAN CORRECTION r6b: preview frames of the lean variants L16 / L12 / L08 from Yoru_Sprint_r6b.blend, plus the two game-camera rows of
# L20 again (into L20b_*, the round-1 frames stay untouched), all with ONE common crop window per row (the union of the four columns' own windows,
# printed by build_sprint_r6b_render.py crop_only=1), so heads and shoulders sit where they really are:
#   wide : game camera, every 2nd frame, 1080p, window = union of the joint windows (round 1 rule)
#   body : game camera zoomed on arms / pistols / upper body, 6400 x 3600 inside the window, union of the windows WITH the head top (head_top=0.23)
#   side : side view 720 x 960 (L20 reuses frames_r6/L20_side)
# The columns render in parallel (one background Blender per column, its rows one after the other).
#   sh build_sprint_r6b_renderall.sh
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
R="C:/Users/valen/ZeroProtocol/Blender"
S="$R/scripts/build_sprint_r6b_render.py"
F="$R/work/Sprint/frames_r6"
EVEN=$(seq -s, 0 2 106)
BL="$R/work/Sprint/Yoru_Sprint_r6b.blend"; GJ="$R/work/Sprint/Yoru_Sprint_r6b_gait.json"
WIN_WIDE="0.38495,0.55621,0.24379,0.54711"
WIN_BODY="0.43446,0.50671,0.39491,0.55617"
column() {   # $1 = column folder name, $2 = action, $3 = 1 to render the side view too
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/$1_wide" "$GJ" view=game action=$2 frames=$EVEN res=1920x1080 crop=wide window=$WIN_WIDE 2>&1 | grep -E "RENDER DONE|WINDOW|Error|Traceback" | sed "s/^/$1 /"
  "$B" -b --factory-startup "$BL" --python "$S" -- "$F/$1_body" "$GJ" view=game action=$2 frames=0-107 res=6400x3600 crop=body head_top=0.23 window=$WIN_BODY 2>&1 | grep -E "RENDER DONE|WINDOW|Error|Traceback" | sed "s/^/$1 /"
  if [ "$3" = "1" ]; then
    "$B" -b --factory-startup "$BL" --python "$S" -- "$F/$1_side" "$GJ" view=side action=$2 frames=0-35 res=720x960 2>&1 | grep -E "RENDER DONE|Error|Traceback" | sed "s/^/$1 /"
  fi
}
column L20b Yoru_Sprint_r6_L20 0 &
column L16 Yoru_Sprint_r6_L16 1 &
column L12 Yoru_Sprint_r6_L12 1 &
column L08 Yoru_Sprint_r6_L08 1 &
wait
echo ALL RENDERS DONE
