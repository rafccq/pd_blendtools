import sys
import os
import time
import pkgutil
import importlib
from math import pi

import bpy
import bmesh
from mathutils import Euler, Vector, Matrix

os.system('cls')

t = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
ln = '\n' + '-'*32 + '\n'
print(ln, t, ln)

# add modules to path
blend_dir = os.path.dirname(bpy.data.filepath)
sys.path.append(blend_dir)

base_dir = f'{blend_dir}/pd_blendtools'
modules_dirs = [base_dir, f'{base_dir}/nodes']

for dir in modules_dirs:
    if dir not in sys.path:
        print('added to path: ', dir)
        sys.path.append(dir)
        
# try to unregister
import nodes.pd_shadernodes as pdn
#try:
#    pdn.unregister()
#except RuntimeError as err:
#    print('unregister error:', err)
#    pass

import pd_blendtools as pdbt
import pd_blendtools.nodes as pdnodes
import typeinfo
importlib.reload(pdbt)
#importlib.reload(pdnodes)
#importlib.reload(typeinfo)

submodules = {}
for modinfo in pkgutil.iter_modules(pdbt.__path__):
    submod = __import__(modinfo.name, globals(), locals(), [], 0)
    submodules[modinfo.name] = importlib.reload(submod)
    print(f'reloaded {modinfo.name}')

#import pd_blendtools.nodes as pdnodes
for modinfo in pkgutil.iter_modules(pdnodes.__path__):
    submod = __import__(modinfo.name, globals(), locals(), [None], 0)
    submodules[modinfo.name] = importlib.reload(submod)
    print(f'reloaded {modinfo.name}')

#importlib.reload(pdnodes)

#print('PATH', pdbt.nodes.__path__)

pdi = submodules['pd_import']
tiles = submodules['tiles_import']
setup = submodules['setup_import']
bgi = submodules['bg_import']
bgu = submodules['bg_utils']
pdm = submodules['pd_materials']
pdu = submodules['pd_utils']
pdp = submodules['pd_addonprefs']
rom = submodules['romdata']
pdops = submodules['pd_ops']


def register():
    pdops.remove_menu()
#    pdn.register()
    tiles.register()
    setup.register()
    bgi.register()
    pdbt.register()


def clear():
    pdi.clear_materials()
    pdu.clear_scene()

def loadmodel(name):
    pdu.ini_file.cache_clear()
    rompath = pdp.pref_get('rompath')
    romdata = rom.Romdata(rompath)
    obj, _ = pdi.import_model(romdata, name, link=False)
    pdu.add_to_collection(obj, 'Props')
    rot_mat = Euler((pi/2, 0, pi/2)).to_matrix().to_4x4()
    obj.matrix_world = rot_mat @ obj.matrix_world


def cl_setup():
    pdu.clear_collection('Props')
    pdu.clear_collection('Intro')

#clear()
#cl_setup()
register()

#loadmodel('ProofgunZ')

#bgu.new_room_from_selection(bpy.context)
#bgu.new_portal_from_selection(bpy.context)
#bgu.new_portal_from_edge(bpy.context)


#bgi.bg_import('bg_dish') # Carrington Institute
#bgi.bg_import('bg_ame') # Defection
#bgi.bg_import('bg_ame', range(0x20, 0x30)) # Defection
#bgi.bg_import('bg_ear') # Investigation
#bgi.bg_import('bg_eld') # Villa
#bgi.bg_import('bg_pete') # Chicago
#bgi.bg_import('bg_pete', range(0x5c, 0x5d)) # Chicago
#bgi.bg_import('bg_lue') # Area 51
#bgi.bg_import('bg_azt') # Crash Site
#bgi.bg_import('bg_rit') # Air Force One

#bgi.bg_import('bg_mp15') # Grid
#bgi.bg_import('bg_mp11') # Felicity
#bgi.bg_import('bg_mp4') # Warehouse
#bgi.bg_import('bg_mp12') # Fortress

# ------------------ SETUPS ------------------
#setup.setup_import('bg_mp15', True)
#setup.setup_import('bg_mp11', True)
#setup.setup_import('bg_mp4', True)
#setup.setup_import('bg_dish')
#setup.setup_import('bg_ame')
#setup.setup_import('bg_pete')
#setup.setup_import('bg_eld')
#setup.setup_import('bg_ear')
#setup.setup_import('bg_rit')
#setup.setup_import('bg_lue')


#pdu.tiles_from_obj(bpy.data.objects['Plane'])

#tiles.bg_loadtiles('bg_mp15')

#pdi.bg_loadroom(0x02)
#pdm.portal_material()
#pdi.bg_portals_hide()
#pdi._bg_loadlights()