import sys
import os
import bpy
from bpy import context as ctx
from mathutils import *

# add modules to path
blend_dir = os.path.dirname(bpy.data.filepath)
modules_dir = f'{blend_dir}\pd_modeltool'

if modules_dir not in sys.path:
    print('added to path: ', modules_dir)
    sys.path.append(modules_dir)

import importlib
import pd_utils as pdu
import pdmodel
import cooking
import bytereader
import struct


modules = [pdu, pdmodel, bytereader, cooking]
for m in modules:
    importlib.reload(m)

import bmesh

def selectFace(idx):
    mesh = bpy.data.meshes['mesh_data.004']
    bm = bmesh.from_edit_mesh(mesh)
    bm.faces[idx].select = True
    bmesh.update_edit_mesh(mesh)

cooking.main()
#selectFace(0)

joints = bpy.data.collections['Joints'].objects
    
def positionJoint(jnum, parents):
#    joint = joints['22.Joint']
    joint = joints[f'{jnum:02X}.Joint']
    pos = joint.location
    #print(pos)

#    pos = Vector((-0.0194306, 20.085030, 2.024232))
#    parents = [0,10,11,20,21]
    for idx in parents:
        name = f'{idx:02X}.Joint'
        p = joints[name].location
        pos += Vector((p.x, p.y, p.z))
        
    joint.location = pos
        
#for e in joints:
#    if '24' not in e.name:
#        e.hide_viewport = True

#joint.location = pos

#joint.matrix_world = mat1

#positionJoint(0x22, [0,0x10,0x11,0x20,0x21])

joint = joints['22.Joint']
bpy.ops.object.select_all(action='DESELECT')
#joint.select_set(True)
#bpy.context.view_layer.objects.active = joint
print('\n'*4)