import os
import bpy

TEMPLATE_NAME = 'PD_MaterialTemplate'
MAT_BLENDFILE = 'pd_materials.blend'
TEX_FOLDER    = '//tex'

TEXFORMAT_RGBA32     = 0x00 # 32-bit RGBA (8/8/8/8)
TEXFORMAT_RGBA16     = 0x01 # 16-bit RGBA (5/5/5/1)
TEXFORMAT_RGB24      = 0x02 # 24-bit RGB (8/8/8)
TEXFORMAT_RGB15      = 0x03 # 15-bit RGB (5/5/5)
TEXFORMAT_IA16       = 0x04 # 16-bit grayscale+alpha
TEXFORMAT_IA8        = 0x05 # 8-bit grayscale+alpha (4/4)
TEXFORMAT_IA4        = 0x06 # 4-bit grayscale+alpha (3/1)
TEXFORMAT_I8         = 0x07 # 8-bit grayscale
TEXFORMAT_I4         = 0x08 # 4-bit grayscale
TEXFORMAT_RGBA16_CI8 = 0x09 # 16-bit 5551 paletted colour with 8-bit palette indexes
TEXFORMAT_RGBA16_CI4 = 0x0a # 16-bit 5551 paletted colour with 4-bit palette indexes
TEXFORMAT_IA16_CI8   = 0x0b # 16-bit 88 paletted greyscale+alpha with 8-bit palette indexes
TEXFORMAT_IA16_CI4   = 0x0c # 16-bit 88 paletted greyscale+alpha with 4-bit palette indexes

G_IM_FMT_RGBA = 0
G_IM_FMT_YUV  = 1
G_IM_FMT_CI   = 2
G_IM_FMT_IA   = 3
G_IM_FMT_I    = 4

G_IM_SIZ_4b  = 0
G_IM_SIZ_8b  = 1
G_IM_SIZ_16b = 2
G_IM_SIZ_32b = 3
G_IM_SIZ_DD  = 5

# TEMP
G_LIGHTING    = 0x00020000
G_TEXTURE_GEN = 0x00040000

def material_remove(name):
    if name not in bpy.data.materials: return
    mat = bpy.data.materials[name]

    tree = mat.node_tree
    img = None
    if 'Image Texture' in tree:
        texnode = tree.nodes['Image Texture']
        img = texnode.image

    bpy.data.materials.remove(mat)

    if img.users == 0:
        imgname = img.name
        bpy.data.images.remove(imgname)

def materials_clear():
    for mat in bpy.data.materials:
        if mat.users == 0: bpy.data.materials.remove(mat)

def tex_has_alpha(fmt, depth):
    if fmt == G_IM_FMT_IA and depth in [G_IM_SIZ_4b, G_IM_SIZ_8b, G_IM_SIZ_16b]: return True
    if fmt == G_IM_FMT_CI and depth in [G_IM_SIZ_4b, G_IM_SIZ_8b]: return True
    if fmt == G_IM_FMT_RGBA and depth in [G_IM_SIZ_4b, G_IM_SIZ_8b, G_IM_SIZ_16b, G_IM_SIZ_32b]: return True

    return False

def tex_smode(smode):
    modemap = { 0: 'REPEAT', 1: 'EXTEND', 2: 'MIRROR' }
    return modemap[smode]

def mat_name(tex, smode, geom_mode):
    smode = f'_{smode:02X}' if smode else ''
    geom_mode = f'_{geom_mode:08X}' if geom_mode else ''
    return f'Mat_{tex:04X}{smode}{geom_mode}'

def material_new(texnum, smode, use_alpha, geom_mode):
    # if there is already a material for this texture/mode, don't create a new one
    name = mat_name(texnum, smode, geom_mode)
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    preset = 'ENV_MAPPING' if geom_mode & (G_TEXTURE_GEN | G_LIGHTING) else 'DIFFUSE'
    mat = material_from_template(name, preset)

    node_tex = mat.node_tree.nodes['teximage']
    node_bsdf = mat.node_tree.nodes['p_bsdf']

    img = f'{texnum:04X}.bmp'
    imglib = bpy.data.images
    node_tex.image = imglib[img] if img in imglib else imglib.load(f'{TEX_FOLDER}/{img}')
    node_tex.extension = tex_smode(smode)

    if use_alpha:
        mat.node_tree.links.new(node_bsdf.inputs['Alpha'], node_tex.outputs['Alpha'])

    return mat

def material_from_template(name, preset):
    if TEMPLATE_NAME not in bpy.data.materials:
        blend_dir = os.path.dirname(bpy.data.filepath)
        with bpy.data.libraries.load(f'{blend_dir}/{MAT_BLENDFILE}') as (data_from, data_to):
            data_to.materials = data_from.materials
            # print(f'template added {data_from.materials}')

    mat = bpy.data.materials[TEMPLATE_NAME].copy()
    mat.name = name

    node_tex = mat.node_tree.nodes['teximage']
    node_texcoord = mat.node_tree.nodes['texcoord']
    node_bsdf = mat.node_tree.nodes['p_bsdf']

    if preset == 'ENV_MAPPING':
        # remove the mixer[Color] -> bsdf[Base Color] link
        links_bsdf = node_bsdf.inputs['Base Color'].links
        for link in links_bsdf: mat.node_tree.links.remove(link)

        mat.node_tree.links.new(node_bsdf.inputs['Base Color'], node_tex.outputs['Color'])
        mat.node_tree.links.new(node_tex.inputs['Vector'], node_texcoord.outputs['Reflection'])

    return mat

