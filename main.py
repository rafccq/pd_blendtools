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

def create_material(mat_name, diffuse_color=(1,1,1,1)):
    mat = bpy.data.materials.new(name=mat_name)
    mat.diffuse_color = diffuse_color
    return mat

def obj_assign_mat(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    # assign materials to faces
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode = 'EDIT')
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    bm.faces.ensure_lookup_table()

    faces = bm.faces

    faces[0].material_index = 0
    faces[1].material_index = 0
    faces[2].material_index = 0
    faces[3].material_index = 0
    bmesh.update_edit_mesh(mesh)
    bpy.ops.object.mode_set(mode = 'OBJECT')
        
def create_tex_material(name, image_filename):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    
    material_shader = material.node_tree.nodes["Principled BSDF"]
    texture = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(f'//tex/{image_filename}')
    material.node_tree.links.new(material_shader.inputs['Base Color'], texture.outputs['Color'])

    return material

def material_remove(name):
    if name not in bpy.data.materials: return
    mat = bpy.data.materials[name]
    bpy.data.materials.remove(mat)
    
def material_test(obj_name, mat_name, img_filename):
#    for material in bpy.data.materials:
#        material.user_clear()
#        bpy.data.materials.remove(material)

    obj = bpy.data.collections['Meshes'].objects[obj_name]
    material_remove(mat_name)
    mat = create_tex_material(mat_name, img_filename)
    obj_assign_mat(obj, mat)
#    bpy.data.materials.remove(material)
#    bpy.context.object.data.materials.clear()

    # Generate 2 demo materials
#    mat_red = create_material("Red", (1,0,0,1))
#    mat_green = create_material("Green", (0,1,0,1))


#    obj_assign_mat(col['07.Mesh-M21'], mat_red, mat_green)
#    obj_assign_mat(col['09.Mesh-M21'], mat_red, mat_green)

#    mat = bpy.data.materials.new(name='Mat.07-0323')
#    bpy.data.materials[name]
    

#obj = bpy.data.collections['Meshes'].objects['07.Mesh-M21']
#bpy.ops.object.select_all(action='DESELECT')
#obj.select_set(True)
#bpy.context.view_layer.objects.active = obj

#selectFace(0)

cmd = [0xB1, 0x00, 0x32, 0x6B, 0x20, 0x10, 0xB5, 0x85]
#print(pdu.read_tri4(cmd))
print('\n'*4)


def uv_from_vert_first(uv_layer, v):
    for l in v.link_loops:
        uv_data = l[uv_layer]
        return uv_data.uv

    return None


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

    for idx,face in enumerate(bm.faces):
        print(f'face {idx}')
        for loop in face.loops:
            print(f' {loop.index} {loop.vert}')
    #        print(loop.vert)

    bm.free()

def test_loops2(obj):
    for loop in obj.data.loops:
        print(f' {loop.index} {loop.vert}')
                
obj = bpy.data.collections['Meshes'].objects['07.Mesh-M21']

test_loops2(obj)
    
#material_test('07.Mesh-M21', 'Mat.07-0323', '0323.bmp')
#cooking.main()