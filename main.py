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