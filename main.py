import sys
import os
import time
import pkgutil
import importlib

import bpy
import bmesh


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
        

import pd_blendtools as pdbt
import typeinfo
importlib.reload(pdbt)
#importlib.reload(typeinfo)

submodules = {}
for modinfo in pkgutil.iter_modules(pdbt.__path__):
    submod = __import__(modinfo.name, globals(), locals(), [], 0)
    submodules[modinfo.name] = importlib.reload(submod)
    print(f'reloaded {modinfo.name}')

pdi = submodules['pd_import']
tiles = submodules['tiles_import']
setup = submodules['setup_import']
bgi = submodules['bg_import']
pdm = submodules['pd_materials']
pdu = submodules['pd_utils']
pdp = submodules['pd_addonprefs']
rom = submodules['romdata']
import nodes.pd_shadernodes as pdn

def register():
    try:
        pdn.unregister()
    except RuntimeError as err:
        print('unregister error:', err)
        pass

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
    pdi.import_model(romdata, name)


#clear()
register()
#loadmodel('PchrremotemineZ')


#pdi.register_handlers()

#bgi.bg_import('bg_ame')
#bgi.bg_import('bg_mp15')
#bgi.bg_import('bg_mp4')
#bgi.bg_import('bg_pete')

#setup.setup_import('bg_mp15', True)
#setup.setup_import('bg_mp4', True)
#setup.setup_import('bg_pete')

#tiles.bg_loadtiles('bg_mp15')

#pdi.bg_loadroom(0x02)
#pdm.portal_material()
#pdi.bg_portals_hide()
#pdi._bg_loadlights()




#flag = tiles.GEOFLAG_FLOOR1
#flag = tiles.GEOFLAG_FLOOR2
#flag = tiles.GEOFLAG_WALL
#flag = tiles.GEOFLAG_BLOCK_SIGHT
#flag = tiles.GEOFLAG_BLOCK_SHOOT
#flag = tiles.GEOFLAG_LIFTFLOORl
#flag = tiles.GEOFLAG_LADDER
#flag = tiles.GEOFLAG_RAMPWALL
#flag = tiles.GEOFLAG_SLOPE
#flag = tiles.GEOFLAG_UNDERWATER
#flag = tiles.GEOFLAG_0400
#flag = tiles.GEOFLAG_AIBOTCROUCH
#flag = tiles.GEOFLAG_AIBOTDUCK
#flag = tiles.GEOFLAG_STEP
#flag = tiles.GEOFLAG_DIE
#flag = tiles.GEOFLAG_LADDER_PLAYERONLY

res, wco, flg, flc, flt = ['reset', 'wallfloor', 'flag', 'floorcol', 'floortype']
#pdi.bg_colortiles(flg, flag=flag)
#tiles.bg_colortiles(flt)

#blend_dir = bpy.path.abspath('//')
#configs = pdu.ini_file(f'{blend_dir}/config.ini')
#print(configs)

#print(pdp.pref_get.cache_info())

#os.system('cls')
#M = bpy.context.scene.objects['Pmulti_ammo_crateZ.009'].matrix_world
#t = [M[i].w for i in range(3)]
#print(M)
#print(t)

#obj = bpy.context.view_layer.objects.active
#M = obj.matrix_world
#print(obj)
#print(M)