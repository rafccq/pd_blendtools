import hashlib

import bpy
from bpy.types import PointerProperty, Panel
from bpy.utils import register_classes_factory

from materials.mat_geomode import *
from materials.mat_setcombine import *
from materials.mat_othermode_h import *
from materials.mat_othermode_l import *
from materials.mat_tex import *

from pd_data.gbi import *
from utils import pd_utils as pdu

from fast64 import f3d
from fast64.f3d import f3d_enums
from fast64.f3d.f3d_material import menu_items_enum, createF3DMat


TEMPLATE_NAME = 'PD_MaterialTemplate'
MAT_BLENDFILE_4X = 'pd_materials.blend'
MAT_BLENDFILE_3X = 'pd_materials_v3_x.blend'

UPPER_MODES = {
    0x4: ('g_mdsft_alpha_dither', f3d_enums.enumAlphaDither),
    0x6: ('g_mdsft_rgb_dither', f3d_enums.enumColorDither),
    0x8: ('g_mdsft_combkey', f3d_enums.enumCombKey),
    0x9: ('g_mdsft_textconv', f3d_enums.enumTextConv),
    0x0c: ('g_mdsft_text_filt', f3d_enums.enumTextFilt),
    0x0e: ('g_mdsft_textlut', f3d_enums.enumTextLUT),
    0x10: ('g_mdsft_textlod', f3d_enums.enumTextLOD),
    0x11: ('g_mdsft_textdetail', f3d_enums.enumTextDetail),
    0x13: ('g_mdsft_textpersp', f3d_enums.enumTextPersp),
    0x14: ('g_mdsft_cycletype', f3d_enums.enumCycleType),
    0x17: ('g_mdsft_pipelinemode', f3d_enums.enumPipelineMode),
}

TEXCONV = { 0b000: 0, 0b101: 1, 0b110: 2, }
TEXFILT = { 0b00: 0, 0b10: 1, 0b11: 2, }
TEXLUT = { 0b00: 0, 0b10: 1, 0b11: 2, }

LOWER_RENDERMODE_FLAGS = {
    1 << 0: 'aa_en',
    1 << 1: 'z_cmp',
    1 << 2: 'z_upd',
    1 << 3: 'im_rd',
    1 << 4: 'clr_on_cvg',
    1 << 9: 'cvg_x_alpha',
    1 << 10: 'alpha_cvg_sel',
    1 << 11: 'force_bl',
}

PORTAL_MAT = 'PD_PortalMat'
WAYPOINT_MAT = 'PD_WaypointMat'
COVER_MAT = 'PD_CoverMat'

class PDMaterialSetup:
    def __init__(self):
        self.texload = 0
        self.texconfig = 0
        self.settimg = 0
        self.othermodeL = {}
        self.othermodeH = {}
        self.geomset = 0
        self.geomclear = 0
        self.setcombine = 0
        self.texnum = -1

        self.applied = 0

    def add_cmd(self, cmd):
        op = cmd[0]
        cmdint = int.from_bytes(cmd, 'big')

        if op == G_PDTEX:
            self.texload = cmdint
            self.texnum = cmdint & 0xfff
        elif op == G_TEXTURE:
            self.texconfig = cmdint
        elif op == G_SetOtherMode_L:
            mode = (cmdint & 0xff0000000000) >> 40
            self.othermodeL[mode] = cmdint
        elif op == G_SetOtherMode_H:
            mode = (cmdint & 0xff0000000000) >> 40
            self.othermodeH[mode] = cmdint
        elif op == G_SETGEOMETRYMODE:
            self.geomset |= cmdint
        elif op == G_CLEARGEOMETRYMODE:
            self.geomclear |= cmdint
            self.geomset &= ~cmdint
        elif op == G_SETCOMBINE:
            self.setcombine = cmdint
        elif op == G_SETTIMG:
            self.settimg = cmdint
            self.texnum = cmdint & 0xffffffff

    def has_envmap(self):
        geo = self.geomset & ~self.geomclear
        return bool(geo & (G_LIGHTING | G_TEXTURE_GEN))

    # returns a ID for this setup, based on the commands/texture id etc
    def id(self):
        mat_id = 'Mat'
        if self.has_texture():
            mat_id += f'-{self.texnum:04X}'

        mat_id += '-'

        cmdid = lambda e: f'{(e & 0xff000000_00000000) >> 56:02X}' if e else ''

        cmds = self.cmdlist()
        for cmd in cmds:
            mat_id += cmdid(cmd)

        return mat_id

    def has_texture(self):
        return self.texnum >= 0

    def hash(self):
        allbytes = bytearray()
        cmds = self.cmdlist()
        for cmd in cmds:
            allbytes += cmd.to_bytes(8, 'big')
        return hashlib.sha256(allbytes).hexdigest()

    def cmdlist(self):
        addcmd = lambda cmds, e: cmds.append(e) if e else None

        allcmds = []
        addcmd(allcmds, self.texload)
        addcmd(allcmds, self.texconfig)

        for _, cmd in self.othermodeL.items():
            addcmd(allcmds, cmd)

        for _, cmd in self.othermodeH.items():
            addcmd(allcmds, cmd)

        addcmd(allcmds, self.setcombine)
        addcmd(allcmds, self.geomset)
        addcmd(allcmds, self.geomclear)

        return allcmds

    def copy(self):
        mat = PDMaterialSetup()
        mat.texload = self.texload
        mat.texconfig = self.texconfig
        mat.othermodeL = self.othermodeL
        for mode, cmd in self.othermodeH.items():
            mat.othermodeH[mode] = cmd

        mat.setcombine = self.setcombine
        mat.geomset = self.geomset
        mat.geomclear = self.geomclear

        return mat


class PDMaterialProperty(PropertyGroup):
    menu_tab: bpy.props.EnumProperty(items=menu_items_enum)

    combiner: PointerProperty(name='combiner', type=MatSetCombine)
    geomode: PointerProperty(name='geomode', type=MatGeoMode)
    othermodeL: PointerProperty(name='othermodeL', type=MatOtherModeL)
    othermodeH: PointerProperty(name='othermodeH', type=MatOtherModeH)
    texconfig: PointerProperty(name='texconfig', type=MatTexConfig)
    texload: PointerProperty(name='texload', type=MatTexLoad)


class PDMaterialPanel(Panel):
    bl_label = "PD Material"
    bl_idname = "MATERIAL_PT_PD_Inspector"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout

        material = context.material
        if material is None or material.is_f3d or not material.is_pd:
            return

        pd_mat = material.pd_mat
        layout = layout.box()
        titleCol = layout.column()
        titleCol.box().label(text="PD Material (Simple)")
        layout.row().prop(pd_mat, "menu_tab", expand=True)

        if pd_mat.menu_tab == 'Combiner':
            mat_setcombine_draw(pd_mat.combiner, layout, context)
        elif pd_mat.menu_tab == 'Geo':
            matgeo_draw(pd_mat.geomode, layout, context)
        elif pd_mat.menu_tab == 'Sources':
            mat_tex_draw(pd_mat, layout, context)
        elif pd_mat.menu_tab == 'Upper':
            mat_othermodeH_draw(pd_mat.othermodeH, layout, context)
        elif pd_mat.menu_tab == 'Lower':
            mat_othermodeL_draw(pd_mat.othermodeL, layout, context)


def material_geomode(mat, cmd, val):
    for flagname, bits in GEO_FLAGS.items():
        if bool(cmd & bits):
            setattr(mat.rdp_settings, flagname, val)

def material_othermodeH(mat, cmd):
    mode = (cmd & 0xff0000000000) >> 40
    bits = (cmd & 0xffffffff) >> mode

    items = UPPER_MODES[mode]
    modename = items[0]
    texmodes = {
        'g_mdsft_textconv': TEXCONV,
        'g_mdsft_text_filt': TEXFILT,
        'g_mdsft_textlut': TEXLUT,
    }

    if modename in texmodes.keys():
        idx = texmodes[modename][bits]
        modeval = items[1][idx][0]
    else:
        modeval = items[1][bits][0]

    # print('  ', modename, modeval)
    setattr(mat.rdp_settings, modename, modeval)

def material_othermodeL(mat, cmd):
    mode = (cmd & 0xff0000000000) >> 40
    bits = (cmd & 0xffffffff) >> mode

    if mode in [MODE_ALPHACMP, MODE_ZSRC]:
        modebits = (cmd & 0xffffffff) >> mode
        items = f3d_enums.enumAlphaCompare if mode == MODE_ALPHACMP else f3d_enums.enumDepthSource
    else: # RENDERMODE
        # cycle independent params
        modebits = (cmd & 0xfff8) >> 3
        for flag, attr in LOWER_RENDERMODE_FLAGS.items():
            setattr(mat.rdp_settings, attr, bool(modebits & flag))

        cvg_dst = (modebits & 0x60) >> 5
        zmode = (modebits & 0x180) >> 7
        setattr(mat.rdp_settings, 'cvg_dst', f3d_enums.enumCoverage[cvg_dst][0])
        setattr(mat.rdp_settings, 'zmode', f3d_enums.enumZMode[zmode][0])

        # cycle dependent params: blend
        blendparams = (cmd & 0xffff0000) >> 16

        # returns the nibble (set of 4 bits) at idx
        _nib = lambda idx: (blendparams & (0xf << (4 * idx))) >> (4 * idx)

        # upper and lower 2 bits in a nibble
        _upp = lambda w: (w & 0xC) >> 2
        _low = lambda w: (w & 0x3)

        b, m, a, p = _nib(0), _nib(1), _nib(2), _nib(3)

        b1, b2 = _upp(b), _low(b)
        m1, m2 = _upp(m), _low(m)
        a1, a2 = _upp(a), _low(a)
        p1, p2 = _upp(p), _low(p)

        names = [f'blend_{p}{n}' for p in ['b', 'm', 'a', 'p'] for n in [1, 2]]
        values = [b1, b2, m1, m2, a1, a2, p1, p2]
        allitems = [
            f3d_enums.enumBlendMix,
            f3d_enums.enumBlendColor,
            f3d_enums.enumBlendAlpha,
            f3d_enums.enumBlendColor,
        ]
        for i, (name, val) in enumerate(zip(names, values)):
            items = allitems[i // 2]
            setattr(mat.rdp_settings, name, items[val][0])

        mat.rdp_settings.set_rendermode = True
        mat.rdp_settings.rendermode_advanced_enabled = True

def material_setcombine(mat, cmd):
    ofs = 0
    mat.set_combiner = True
    for name, w in COMBINER_PARAMWIDTHS.items():
        mask = (1 << w) - 1
        idx = cmd & mask

        combiner = mat.combiner1 if 'combiner1' in name else mat.combiner2
        param = name[len('combinerX_')].upper()
        alpha = 'alpha' in name
        attr = param + '_alpha' if alpha else param

        # handles some param values that have discontinuity
        if 'B' in param:
            idx = 8 if idx == 15 else idx
        elif param == 'C' and not alpha:
            idx = 0x10 if idx == 0x1f else idx

        key = f'Case {param}'
        key += " Alpha" if alpha else ''
        items = f3d_enums.combiner_enums[key]
        setattr(combiner, attr, items[idx][0])

        cmd >>= w
        ofs += w

def material_settex(mat, cmd):
    texnum = cmd & 0xfff
    texname = f'{texnum:04X}.png'

    tex0 = mat.tex0
    tex0.tex = bpy.data.images[texname]
    tex0.tex_set = True

    w0 = (cmd & 0xffffffff00000000) >> 32
    smode = bool((w0 >> 22) & 0x3)
    tex0.S.clamp = smode == 1
    tex0.T.clamp = smode == 1
    tex0.S.mirror = smode == 2
    tex0.T.mirror = smode == 2
    tex0.shift_s = (w0 >> 14) & 0xf
    tex0.shift_t = (w0 >> 10) & 0xf
    tex0.lod_flag = bool(w0 & 0x200)
    tex0.subcmd = w0 & 0x7

    tex0.S.high = tex0.tex.size[0] - 1
    tex0.T.high = tex0.tex.size[1] - 1

def connect(node_tree, src, dst_node, dst_field):
    nodes = node_tree.nodes
    src_node, src_field = src.split('.')
    node_tree.links.new(nodes[src_node].outputs[src_field], nodes[dst_node].inputs[dst_field])

def mat_clear_node_inputs(mat, node):
    node_tree = mat.node_tree
    for input in node.inputs:
        for link in input.links:
            node_tree.links.remove(link)

def mat_presetcombine(mat):
    if mat.f3d_mat.set_combiner: return

    node_tree = mat.node_tree
    nodes = mat.node_tree.nodes

    mat_clear_node_inputs(mat, nodes["Cycle_1"])

    connect(node_tree, 'Tex1_I.Color', 'Cycle_1', 0) # 'A'
    connect(node_tree, 'Tex0_I.Color', 'Cycle_1', 1) # 'B'
    connect(node_tree, 'CombinerInputs.LOD Fraction', 'Cycle_1', 2) # 'C'
    connect(node_tree, 'Tex0_I.Color', 'Cycle_1', 3) # 'D'
    connect(node_tree, 'Tex1_I.Alpha', 'Cycle_1', 4) # 'Aa'
    connect(node_tree, 'Tex0_I.Alpha', 'Cycle_1', 5) # 'Ba'
    connect(node_tree, 'CombinerInputs.LOD Fraction', 'Cycle_1', 6) # 'Ca'
    connect(node_tree, 'Tex0_I.Alpha', 'Cycle_1', 7) # 'Da'

def material_create_f3d(bl_obj, matsetup, name):
    mat = createF3DMat(bl_obj)
    mat.name = name

    matf3d = mat.f3d_mat
    matf3d.set_combiner = False
    for cmd in matsetup.cmdlist():
        op = (cmd & 0xff000000_00000000) >> 56
        if op == G_SETGEOMETRYMODE:
            material_geomode(matf3d, cmd, True)
        elif op == G_CLEARGEOMETRYMODE:
            # material_geomode(matf3d, cmd, False) #TODO
            pass
        elif op == G_SetOtherMode_H:
            material_othermodeH(matf3d, cmd)
        elif op == G_SetOtherMode_L:
            material_othermodeL(matf3d, cmd)
        elif op == G_SETCOMBINE:
            material_setcombine(matf3d, cmd)
        if op == G_PDTEX:
            material_settex(matf3d, cmd)

    return mat

def mat_find_by_hash(bl_obj, hash):
    mats = bl_obj.data.materials
    for mat in mats:
        if mat.hashed == hash:
            return mat

    return None

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
    if fmt == G_IM_FMT_RGBA: return True

    return False

def tex_smode_(smode):
    modemap = { 0: 'REPEAT', 1: 'EXTEND', 2: 'MIRROR' }
    return modemap[smode]

def tex_smode(cmd_texload):
    w0 = (cmd_texload & 0xffffffff00000000) >> 32
    smode = (w0 >> 22) & 3

    modemap = { 0: 'REPEAT', 1: 'EXTEND', 2: 'MIRROR' }
    return modemap[smode]

def mat_name(tex, smode, geom_mode):
    smode = f'_{smode:02X}' if smode else ''
    geom_mode = f'_{geom_mode:08X}' if geom_mode else ''
    return f'Mat_{tex:04X}{smode}{geom_mode}'

def material_setup_nodes(nodetree, matsetup):
    cmds = matsetup.cmdlist()
    if not cmds: return

    space = 20
    node_prev = nodetree.nodes['pdmaterial']
    for cmd in cmds:
        op = (cmd & 0xff000000_00000000) >> 56
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
        elif op == G_SETTIMG:
            new_node = nodetree.nodes.new('pd.nodes.settimg')
        elif op == G_PDTEX:
            new_node = nodetree.nodes.new('pd.nodes.textureload')
        elif op == G_SETCOMBINE:
            new_node = nodetree.nodes.new('pd.nodes.setcombine')
        else:
            # TODO logger
            print(f'WARNING unsupported material cmd: {op:02X}')
            continue

        cmdstr = f'{cmd:08X}'
        new_node.set_cmd(cmdstr)

        frame = nodetree.nodes['pdframe']
        new_node.parent = frame

        # w = node_prev.min_width if node_prev.min_width else 150
        new_node.location = node_prev.location
        new_node.location.x += node_prev.width + space
        # w = new_node.min_width if new_node.min_width else 150
        new_node.width = new_node.min_width if new_node.min_width else 150

        nodetree.links.new(new_node.inputs['prev'], node_prev.outputs['next'])
        new_node.post_init()

        node_prev = new_node

def material_new(matsetup, use_alpha):
    name = matsetup.id()+'_PD'
    # if there is already a material for this texture/mode, don't create a new one
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    has_envmap = matsetup.has_envmap()
    preset = 'ENV_MAPPING' if has_envmap else 'DIFFUSE'
    mat = material_from_template(name, preset)
    mat.is_pd = True

    node_tex = mat.node_tree.nodes['teximage']
    node_bsdf = mat.node_tree.nodes['p_bsdf']
    node_vtxcolor = mat.node_tree.nodes['vtxcolor']
    node_vtxcolor.layer_name = 'Col'

    texnum = matsetup.texnum & 0xffffff
    img = f'{texnum:04X}.png'
    imglib = bpy.data.images
    node_tex.image = imglib[img]
    node_tex.extension = tex_smode(matsetup.texload)

    if use_alpha:
        mat.node_tree.links.new(node_bsdf.inputs['Alpha'], node_tex.outputs['Alpha'])

    # material_setup_nodes(mat.node_tree, matsetup)
    material_setup_props(mat, matsetup)

    if bpy.app.version < (4, 0, 0):
        if use_alpha and not material_has_lighting(mat):
            mat.blend_method = 'BLEND'

        # to avoid transparency issues in earlier versions
        mat.show_transparent_back = False

    mat['has_envmap'] = has_envmap

    return mat

def material_setup_props(mat, matsetup):
    pd_mat = mat.pd_mat

    matgeo_set(pd_mat.geomode, matsetup.geomset)
    # matgeoclear_set(pd_mat.geoclear, matsetup.geomclear)

    for cmd in matsetup.othermodeL.values():
        mat_othermodeL_set(pd_mat.othermodeL, cmd)

    for cmd in matsetup.othermodeH.values():
        mat_othermodeH_set(pd_mat.othermodeH, cmd)

    mat_setcombine_set(pd_mat.combiner, matsetup.setcombine)
    mat_texconfig_set(pd_mat.texconfig, matsetup.texconfig)
    mat_texload_set(pd_mat.texload, matsetup.texload)

def mat_show_vtxcolors(mat):
    node_bsdf = mat.node_tree.nodes['p_bsdf']
    node_vtxcolor = mat.node_tree.nodes['vtxcolor']
    mat.node_tree.links.new(node_bsdf.inputs['Base Color'], node_vtxcolor.outputs['Color'])

def mat_remove_links(mat, nodename, inputnames):
    node = mat.node_tree.nodes[nodename]
    for inputname in inputnames:
        links = node.inputs[inputname].links
        for link in links:
            mat.node_tree.links.remove(link)

def mat_set_basecolor(mat, color):
    mat.node_tree.nodes['p_bsdf'].inputs['Base Color'].default_value = color

def material_from_template(name, preset):
    if TEMPLATE_NAME not in bpy.data.materials:
        assets_path = pdu.assets_path()
        blend_file = MAT_BLENDFILE_4X if bpy.app.version >= (4, 0, 0) else MAT_BLENDFILE_3X
        with bpy.data.libraries.load(f'{assets_path}/{blend_file}') as (data_from, data_to):
            data_to.materials = data_from.materials

    bpy.data.materials[TEMPLATE_NAME].use_fake_user = True
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

def material_get_setup(mat):
    node_setup = None
    for node in mat.node_tree.nodes:
        if node.bl_idname == 'pd.nodes.materialsetup':
            node_setup = node
            break
    return node_setup

def material_get_teximage(mat):
    for node in mat.node_tree.nodes:
        if node.bl_idname == 'ShaderNodeTexImage':
            return node.image
    return None

def material_has_lighting(mat):
    node = material_get_setup(mat)

    has_lighting = False
    while node:
        if len(node.outputs[0].links) == 0: break

        node = node.outputs[0].links[0].to_node
        if node.bl_idname == 'pd.nodes.setgeometrymode':  # TMP TODO add const
            has_lighting = node['g_lighting']

    return bool(has_lighting)

def material_has_geo(mat):
    node = material_get_setup(mat)

    # TMP TODO add const
    geo_nodes = ['pd.nodes.setgeometrymode', 'pd.nodes.cleargeometrymode']
    while node:
        if len(node.outputs[0].links) == 0: break

        node = node.outputs[0].links[0].to_node
        if node.bl_idname in geo_nodes:
            return True

    return False

def material_lastnode(mat):
    node = material_get_setup(mat)
    while node:
        if len(node.outputs[0].links) == 0: break
        node = node.outputs[0].links[0].to_node

    return node

from nodes.shadernode_othermode_h import PD_ShaderNodeSetOtherModeH, UPPER_TEXLOD
# TODO TEMP: pre-calculate all mode bits instead of this
def material_texlod(mat):
    node = material_get_setup(mat)

    lod = None
    while node:
        if len(node.outputs[0].links) == 0: break

        node = node.outputs[0].links[0].to_node
        if node.bl_idname == PD_ShaderNodeSetOtherModeH.bl_idname:
            if node.mode == 'g_mdsft_texlod':
                lod = node.g_mdsft_texlod == UPPER_TEXLOD[1][0].lower()

    return lod

def material_cmds(mat):
    geobits = 0
    node = material_get_setup(mat)
    cmds = []
    while node:
        if len(node.outputs[0].links) == 0: break

        node = node.outputs[0].links[0].to_node
        # print(f'   {node.bl_label:<14} {node.get_cmd()}')

        if node.bl_idname == 'pd.nodes.setgeometrymode':
            cmd = int(node.get_cmd(), 16) & 0xffffffff
            geobits |= cmd

        if node.bl_idname == 'pd.nodes.cleargeometrymode':
            cmd = int(node.get_cmd(), 16) & 0xffffffff
            geobits &= ~cmd

        cmds.append(node.get_cmd())

    return cmds, geobits

def _material_export(mat, prevmat):
    if mat.is_f3d:
        return material_export_f3d(mat, prevmat)
    elif mat.is_pd:
        return material_export_pd(mat, prevmat)

def get_texload(mat):
    if mat.is_pd: return mat.pd_mat.texload
    elif mat.is_f3d: return mat.f3d_mat.tex0
    return None

def mat_attr(mat, attr_pd, attr_f3d):
    if not mat: return None
    if mat.is_pd: return getattr(mat.pd_mat, attr_pd)
    elif mat.is_f3d: return getattr(mat.f3d_mat, attr_f3d)

    print(f'WARNING: trying to export invalid material: {mat.name}')
    return None

def material_export(mat, prevmat):
    cmds = []

    mat_prop = lambda mat0, mat1, prop_pd, prop_f3d: [mat_attr(m, prop_pd, prop_f3d) for m in [mat0, mat1]]

    cmds += export_othermodeH(*mat_prop(mat, prevmat, prop_pd='othermodeH', prop_f3d='rdp_settings'))
    cmds += export_othermodeL(*mat_prop(mat, prevmat, prop_pd='othermodeL', prop_f3d='rdp_settings'))

    cmd_combiner = export_combiner(mat, prevmat)
    if cmd_combiner:
        cmds.append(cmd_combiner)

    cmd_texconfig = export_texconfig(*mat_prop(mat, prevmat, prop_pd='texconfig', prop_f3d='tex0'))
    if cmd_texconfig:
        cmds.append(cmd_texconfig)

    cmd_texload = export_texload(*mat_prop(mat, prevmat, prop_pd='texload', prop_f3d='tex0'))
    if cmd_texload:
        cmds.append(cmd_texload)

    cmd_geo = export_geo(*mat_prop(mat, prevmat, prop_pd='geomode', prop_f3d='rdp_settings'))
    if cmd_geo:
        cmds.append(cmd_geo)

    return cmds

def diff(settings0, settings1, propname):
    attr = getattr(settings0, propname)
    return attr != 'NOT_SET' and (not settings1 or attr != getattr(settings1, propname))

def export_geo(geo, prev_geo):
    cmd = geo_command(geo)
    prevcmd = geo_command(prev_geo) if prev_geo else 0

    return cmd if cmd != prevcmd else 0

def export_texload(texload, prev_texload):
    cmd = texload_command(texload)
    prevcmd = texload_command(prev_texload) if prev_texload else 0
    return cmd if cmd != prevcmd else 0

def get_texscale(texconfig):
    s = texconfig.tex_scale[0]
    t = texconfig.tex_scale[1]

    s = int(texconfig.tex_scale[0] * 2 ** 16) if s != 1.0 else 0xFFFF
    t = int(texconfig.tex_scale[1] * 2 ** 16) if t != 1.0 else 0xFFFF
    return s, t

def export_texconfig(texconfig, prev_texconfig):
    s, t = texconfig.get_texscale()
    b = texconfig.tile_index | (texconfig.max_lods << 3)
    return (0xbb00 << 8*6) | (b << 8*5) | (1 << 8*4) | (s << 8*2) | t

def combiner_params(mat):
    params = {}

    if mat.is_pd:
        combiner = mat.pd_mat.combiner
        if not combiner.set_combiner: return {}

        params = {name: pdu.enum_value(combiner, name) for name in COMBINER_PARAMWIDTHS.keys()}
    elif mat.is_f3d:
        matf3d = mat.f3d_mat
        if not matf3d.combiner1.set_combiner: return {}

        for name in COMBINER_PARAMWIDTHS.keys():
            combiner = matf3d.combiner1 if '1' in name else matf3d.combiner2
            src = name[len('combinerX_')].upper()
            alpha = '_alpha' if alpha in name else ''
            params[name] = pdu.enum_value(combiner, f'{src}{alpha}')

    return params

def export_combiner(mat, prev_mat):
    combiner = mat.pd_mat.combiner if mat.is_pd else mat.f3d_mat.combiner1

    if not combiner.set_combiner: return 0

    getcmd = lambda m: combiner_command(combiner_params(m))
    cmd = getcmd(mat)
    prevcmd = getcmd(prev_mat) if prev_mat else 0

    return cmd if cmd != prevcmd else 0

def export_othermodeL(othermodeL, prev_othermodeL):
    cmds = []
    # export alphacompare and zsource modes
    for modename, _, mode in LOWER_MODES[:2]:
        if diff(othermodeL, prev_othermodeL, modename):
            ofs = mode
            propval = pdu.enum_value(othermodeL, modename)

            modebits = propval << ofs
            n = 2 if mode == MODE_ALPHACMP else 1

            cmd = (0xB900 << 8 * 6) | (mode << 8*5) | (n << 8 * 4) | modebits
            cmds.append(cmd)

    # export alphacompare and zsource modes
    if othermodeL.set_rendermode:
        cmd = othermodeL_rendermode_cmd(othermodeL)
        prevcmd = othermodeL_rendermode_cmd(prev_othermodeL) if prev_othermodeL else 0

        if cmd != prevcmd:
            cmds.append(cmd)

    return cmds

def export_othermodeH(othermodeH, prev_othermodeH):
    cmds = []
    for ofs, (modename, _) in UPPER_MODES.items():
        if diff(othermodeH, prev_othermodeH, modename):
            n = UPPER_MODE_WIDTHS[modename]
            modes = UPPER_ITEMS['mode']
            modeval = pdu.enum_value(othermodeH, modename)
            mode_bits = modeval << ofs

            cmd = (0xBA00 << 8*6) | (ofs << 8*5) | (n << 8*4) | mode_bits
            cmds.append(cmd)

    return cmds

def create_basic_material(name, color = None, alpha = 0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    newmat = bpy.data.materials.new(name)
    newmat.use_nodes = True
    newmat.use_fake_user = True
    nodes = newmat.node_tree.nodes

    for node in nodes:
        nodes.remove(node)

    links = newmat.node_tree.links

    # create the basic material nodes
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_output.location.x += 200
    node_pbsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_pbsdf.location = 0, 0
    node_pbsdf.inputs['Alpha'].default_value = alpha

    if color:
        node_pbsdf.inputs['Base Color'].default_value = color

    if alpha < 1.0:
        newmat.blend_method = 'BLEND'

    links.new(node_pbsdf.outputs['BSDF'], node_output.inputs['Surface'])
    newmat.use_backface_culling = True

    return newmat

def portal_material():
    return create_basic_material(PORTAL_MAT)

def waypoint_material():
    return create_basic_material(WAYPOINT_MAT, (0.0, 0.8, 0.0, 1.0), 1.0)

def cover_material():
    return create_basic_material(COVER_MAT, (0.8, 0.0, 0.0, 1.0), 1.0)
