import bpy

# Automatische Zuordnung: VRM-Knochen -> Typische Mixamo / ActorCore Knochennamen
MAPPING = {
    "J_Bip_C_Hips": ["mixamorig:Hips", "Hips", "hip", "pelvis"],
    "J_Bip_C_Spine": ["mixamorig:Spine", "Spine", "spine_01"],
    "J_Bip_C_Chest": ["mixamorig:Spine1", "Spine1", "spine_02"],
    "J_Bip_C_UpperChest": ["mixamorig:Spine2", "Spine2", "spine_03"],
    "J_Bip_C_Neck": ["mixamorig:Neck", "Neck", "neck_01"],
    "J_Bip_C_Head": ["mixamorig:Head", "Head", "head"],
    # Linker Arm
    "J_Bip_L_Shoulder": ["mixamorig:LeftShoulder", "LeftShoulder", "clavicle_l"],
    "J_Bip_L_UpperArm": ["mixamorig:LeftArm", "LeftArm", "upperarm_l"],
    "J_Bip_L_LowerArm": ["mixamorig:LeftForeArm", "LeftForeArm", "lowerarm_l"],
    "J_Bip_L_Hand": ["mixamorig:LeftHand", "LeftHand", "hand_l"],
    # Rechter Arm
    "J_Bip_R_Shoulder": ["mixamorig:RightShoulder", "RightShoulder", "clavicle_r"],
    "J_Bip_R_UpperArm": ["mixamorig:RightArm", "RightArm", "upperarm_r"],
    "J_Bip_R_LowerArm": ["mixamorig:RightForeArm", "RightForeArm", "lowerarm_r"],
    "J_Bip_R_Hand": ["mixamorig:RightHand", "RightHand", "hand_r"],
    # Linkes Bein
    "J_Bip_L_UpperLeg": ["mixamorig:LeftUpLeg", "LeftUpLeg", "thigh_l"],
    "J_Bip_L_LowerLeg": ["mixamorig:LeftLeg", "LeftLeg", "calf_l"],
    "J_Bip_L_Foot": ["mixamorig:LeftFoot", "LeftFoot", "foot_l"],
    "J_Bip_L_ToeBase": ["mixamorig:LeftToeBase", "LeftToeBase", "toe_l"],
    # Rechtes Bein
    "J_Bip_R_UpperLeg": ["mixamorig:RightUpLeg", "RightUpLeg", "thigh_r"],
    "J_Bip_R_LowerLeg": ["mixamorig:RightLeg", "RightLeg", "calf_r"],
    "J_Bip_R_Foot": ["mixamorig:RightFoot", "RightFoot", "foot_r"],
    "J_Bip_R_ToeBase": ["mixamorig:RightToeBase", "RightToeBase", "toe_r"],
}

def retarget(source_name=None, target_name=None):
    armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if len(armatures) < 2:
        print("FEHLER: Du brauchst 2 Armatures in der Szene: Yoru (VRM) und die importierte FBX!")
        return

    # Automatische Erkennung falls nicht angegeben:
    target = None  # Yoru
    source = None  # FBX Animation

    for a in armatures:
        bone_names = [b.name for b in a.data.bones]
        if any("J_Bip" in b for b in bone_names):
            target = a
        elif any("mixamo" in b.lower() or b in ["Hips", "hips"] for b in bone_names):
            source = a

    if not target or not source:
        # Fallback auf Auswahl
        selected = bpy.context.selected_objects
        if len(selected) == 2:
            source, target = selected[0], selected[1]
        else:
            print("Konnte Armatures nicht eindeutig zuordnen. Bitte erst FBX anwählen, dann Yoru mit Shift!")
            return

    print(f"Retargeting von '{source.name}' (FBX) auf '{target.name}' (Yoru VRM)...")

    # Alte Constraints säubern
    for pb in target.pose.bones:
        for c in pb.constraints:
            if c.name.startswith("Retarget_"):
                pb.constraints.remove(c)

    # Constraints anlegen
    source_bones = {b.name for b in source.data.bones}
    mapped_count = 0

    for vrm_bone, candidates in MAPPING.items():
        if vrm_bone not in target.pose.bones:
            continue
        
        # Finde passenden Knochen in der FBX
        match = None
        for cand in candidates:
            if cand in source_bones:
                match = cand
                break
        
        if match:
            pb = target.pose.bones[vrm_bone]
            c = pb.constraints.new('COPY_TRANSFORMS')
            c.name = f"Retarget_{match}"
            c.target = source
            c.subtarget = match
            mapped_count += 1

    print(f"FERTIG! {mapped_count} Knochen erfolgreich verlinkt. Drücke LEERTASTE in Blender!")

if __name__ == "__main__":
    retarget()
