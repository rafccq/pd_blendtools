import sys
import os
import bpy
from bpy import context as ctx
from mathutils import *

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

import pd_gbi as gbi
import cooking
import bytereader
import struct


modules = [pdu, gbi, pdm, base, pdmodel, bytereader, cooking]
modules += [base, otherH, otherL, geo, tex, comb, pdn]

for m in modules:
    importlib.reload(m)

import bmesh

def selectFace(idx):
    mesh = bpy.data.meshes['mesh_data.004']
    bm = bmesh.from_edit_mesh(mesh)
    bm.faces[idx].select = True
    bmesh.update_edit_mesh(mesh)


#obj = bpy.data.collections['Meshes'].objects['07.Mesh-M21']
#bpy.ops.object.select_all(action='DESELECT')
#obj.select_set(True)
#bpy.context.view_layer.objects.active = obj

#selectFace(0)

cmd = [0xB1, 0x00, 0x32, 0x6B, 0x20, 0x10, 0xB5, 0x85]
#print(pdu.read_tri4(cmd))
print('\n'*4)


def test_loops(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode = 'EDIT')
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    bm.faces.ensure_lookup_table()

    '''
    uv_layer = bm.loops.layers.uv.active
    print('UV: ', uv_layer)

    for v in bm.verts:
        uv_first = uv_from_vert_first(uv_layer, v)
        print('v {v} uv {uv_first}')
    '''

    for idx, face in enumerate(bm.faces):
        print(f'face {idx}')
        for loop in face.loops:
            print(f' {loop.index} {loop.vert} {face.index}')
    #        print(loop.vert)
    
    print('loops ', len(obj.data.loops))
    print('faces ', len(bm.faces))

    bm.free()

def test_loops2(obj):
    for loop in obj.data.loops:
        v = obj.data.vertices[loop.vertex_index]
        print(f' {loop.index} {v.co} {type(loop)}')
                
#obj = bpy.data.collections['Meshes'].objects['07.Mesh-M21']
#obj = bpy.data.collections['Meshes'].objects['02.Mesh[0]-M24']
#uv = obj.data.uv_layers.new(name='NewUV')

#test_loops(obj)

#dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PD_Materials.blend")

#print('mat11: ', 'mat11' in bpy.data.materials)
#print('mat idx: ', obj.data.materials.find('mat11'))
#print('mat len: ', len(bpy.data.materials))
#print('mat idx: ', type(obj.data.materials))
#material_test('0B.Mesh-M26', 'Mat.0B-0323', '0323.bmp')
cooking.main()