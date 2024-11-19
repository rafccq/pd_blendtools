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
import nodes.shadernode_tex as nodetex
import nodes.shadernode_setcombine as comb
import nodes.nodeutils as ndu
import export as exp
import bitreader as br
import texload as tex
import imageutils as imu
import romdata as rom

import color_panel as colp
import mtxpalette as mtx
import datablock as dat
import typeinfo as typ

import gbi
import pd_import as pdi
import bytereader
import struct

os.system('cls')

modules = [pdu, typ, gbi, pdm, base, dat, bytereader, pdmodel, pdi, colp, mtx]
modules += [ndu, base, otherH, otherL, geo, nodetex, comb, pdn, exp, br, tex, imu, rom]

for m in modules:
    importlib.reload(m)
    

t = strftime("%Y-%m-%d %H:%M:%S", gmtime())

ln = '\n' + '-'*32 + '\n'
print(ln, t, ln)

def clearLib():
    imglib = bpy.data.images
    for img in imglib:
        imglib.remove(img)
        
    matlib = bpy.data.materials
    for mat in matlib:
        if mat.name.startswith('Mat-'):
            matlib.remove(mat)
            
def load():
    clearLib()
    pdi.main()
    
def exp():
    root = list(filter(lambda e: e.name[-1]=='Z', bpy.data.objects))[0]
    pdi.export(root.name)
    
#pdi.register()
load()
#exp()


#pdu.select('vtx', 99)
#pdu.select('face', 12)
