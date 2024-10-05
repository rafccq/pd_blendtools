import sys
import os
import bpy
from bpy import context as ctx
from mathutils import *
import bmesh
from time import gmtime, strftime
import os

# add modules to path
blend_dir = os.path.dirname(bpy.data.filepath)

base_dir = f'{blend_dir}/pd_modeltool'
modules_dirs = [base_dir, f'{base_dir}/nodes']

for dir in modules_dirs:
    if dir not in sys.path:
        print('added to path: ', dir)
        sys.path.append(dir)


import importlib
import pd_utils as pdu
import pdmodel
import pd_materials as pdm
import nodes.pd_shadernodes as pdn
import nodes.shadernode_base as base
import nodes.shadernode_othermode_h as otherH
import nodes.shadernode_othermode_l as otherL
import nodes.shadernode_geomode as geo
import nodes.shadernode_tex as tex
import nodes.shadernode_setcombine as comb
import nodes.nodeutils as ndu
import export as exp

import gbi
import cooking
import bytereader
import struct

os.system('cls')

modules = [pdu, gbi, pdm, base, pdmodel, bytereader, cooking]
modules += [ndu, base, otherH, otherL, geo, tex, comb, pdn, exp]

for m in modules:
    importlib.reload(m)
    

t = strftime("%Y-%m-%d %H:%M:%S", gmtime())

ln = '\n' + '-'*32 + '\n'
print(ln, t, ln)


def test_loops(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode = 'EDIT')
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    bm.faces.ensure_lookup_table()

    for idx, face in enumerate(bm.faces):
        print(f'face {idx}')
        for loop in face.loops:
            print(f' {loop.index} {loop.vert} {face.index}')
    
    print('loops ', len(obj.data.loops))
    print('faces ', len(bm.faces))

    bm.free()

def test_loops2(obj):
    for loop in obj.data.loops:
        v = obj.data.vertices[loop.vertex_index]
        print(f' {loop.index} {v.co} {type(loop)}')
                

cooking.main()
root = list(filter(lambda e: e.name[-1]=='Z', bpy.data.objects))[0]
cooking.export(root.name)

#pdu.select('vtx', 466)
#pdu.select('face', 12)