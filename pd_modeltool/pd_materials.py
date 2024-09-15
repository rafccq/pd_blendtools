import os
import bpy

from gbi import *

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

class PDMaterialSetup:
    def __init__(self, current_mat=None):
        self.texnum = current_mat.texnum if current_mat else 0
        self.loadtex = False
        self.cmds = []
        self.smode = current_mat.smode if current_mat else 0
        self.geom_mode = current_mat.geom_mode if current_mat else 0
        self.applied = False

    def add_cmd(self, cmd):
        op = cmd[0]
        cmdint = int.from_bytes(cmd, 'big')
        w0 = (cmdint & 0xffffffff00000000) >> 32
        w1 = cmdint & 0xffffffff
        if op == G_PDTEX:
            self.texnum = cmdint & 0xffff
            self.loadtex = True
            self.smode = (w0 >> 22) & 3
        elif op == G_SETGEOMETRYMODE:
            self.geom_mode = w1
        elif op == G_CLEARGEOMETRYMODE:
            self.geom_mode = 0

        self.cmds.append(cmd)

    # returns a ID for this setup, based on the commands/texture id etc
    def id(self):
        mat_id = 'Mat'
        if self.has_texture():
            mat_id += f'-{self.texnum:04X}'

        if len(self.cmds): mat_id += '-'

        for cmd in self.cmds:
            mat_id += f'{cmd[0]:02X}'

        return mat_id

    def has_texture(self):
        return self.texnum >= 0

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

def material_setup_cmds(nodetree, matsetup):
    cmds = matsetup.cmds
    if len(cmds) <= 1: return

    space = 20
    node_prev = nodetree.nodes['pdmaterial']
    for cmd in cmds:
        op = cmd[0]
        if op == G_SETGEOMETRYMODE:
            new_node = nodetree.nodes.new('pd.nodes.setgeometrymode')
        elif op == G_CLEARGEOMETRYMODE:
            new_node = nodetree.nodes.new('pd.nodes.cleargeometrymode')
        elif op == G_SetOtherMode_L:
            new_node = nodetree.nodes.new('pd.nodes.setothermodeL')
        elif op == G_SetOtherMode_H:
            new_node = nodetree.nodes.new('pd.nodes.setothermodeH')
        elif op == G_TEXTURE:
            new_node = nodetree.nodes.new('pd.nodes.textureconfig')
        elif op == G_PDTEX:
            new_node = nodetree.nodes.new('pd.nodes.textureload')
        elif op == G_SETCOMBINE:
            new_node = nodetree.nodes.new('pd.nodes.setcombine')
        else:
            # TODO logger
            print(f'WARNING unsupported material cmd: {op:02X}')
            continue

        cmdstr = ''.join(f'{b:02X}' for b in cmd)
        new_node.set_cmd(cmdstr)

        frame = nodetree.nodes['pdframe']
        new_node.parent = frame

        # w = node_prev.min_width if node_prev.min_width else 150
        new_node.location = node_prev.location
        new_node.location.x += node_prev.width + space
        # w = new_node.min_width if new_node.min_width else 150
        new_node.width = new_node.min_width if new_node.min_width else 145

        nodetree.links.new(new_node.inputs['prev'], node_prev.outputs['next'])
        new_node.post_init()

        node_prev = new_node

def material_new(matsetup, use_alpha):
    name = matsetup.id()
    # if there is already a material for this texture/mode, don't create a new one
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    preset = 'ENV_MAPPING' if matsetup.geom_mode & (G_TEXTURE_GEN | G_LIGHTING) else 'DIFFUSE'
    mat = material_from_template(name, preset)

    node_tex = mat.node_tree.nodes['teximage']
    node_bsdf = mat.node_tree.nodes['p_bsdf']

    img = f'{matsetup.texnum:04X}.bmp'
    imglib = bpy.data.images
    node_tex.image = imglib[img] if img in imglib else imglib.load(f'{TEX_FOLDER}/{img}')
    node_tex.extension = tex_smode(matsetup.smode)

    if use_alpha:
        mat.node_tree.links.new(node_bsdf.inputs['Alpha'], node_tex.outputs['Alpha'])

    material_setup_cmds(mat.node_tree, matsetup)

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

