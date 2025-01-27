import bpy

from gbi import *
import pd_utils as pdu

TEMPLATE_NAME = 'PD_MaterialTemplate'
MAT_BLENDFILE_4X = 'pd_materials.blend'
MAT_BLENDFILE_3X = 'pd_materials_v3_x.blend'

class PDMaterialSetup:
    def __init__(self, mesh_idx, current_mat=None):
        self.texnum = current_mat.texnum if current_mat else -1
        self.loadtex = False
        self.cmds = []
        self.smode = current_mat.smode if current_mat else 0
        self.geom_mode = current_mat.geom_mode if current_mat else 0
        self.applied = False
        self.optimized = False
        self.mesh_idx = mesh_idx

        if current_mat:
            self.cmds_from_mat(current_mat)

    def cmds_from_mat(self, mat):
        for cmd in mat.cmds:
            self.add_cmd(cmd)

    def find_cmd(self, op):
        for idx, cmd in enumerate(self.cmds):
            if cmd[0] == op:
                return idx, cmd
        return -1, None

    def add_cmd(self, cmd):
        op = cmd[0]
        cmdint = int.from_bytes(cmd, 'big')
        w0 = (cmdint & 0xffffffff00000000) >> 32
        w1 = cmdint & 0xffffffff
        if op == G_PDTEX:
            self.texnum = cmdint & 0xfff
            self.loadtex = True
            self.smode = (w0 >> 22) & 3
        elif op == G_SETTIMG:
            self.texnum = cmdint & 0xffffffff
            self.loadtex = True
        elif op == G_SETGEOMETRYMODE:
            self.geom_mode = w1
        elif op == G_CLEARGEOMETRYMODE:
            self.geom_mode = 0

        # if this material already has these cmds, just replace it
        (idx, current) = self.find_cmd(op) if op in [G_PDTEX, G_SETTIMG] else (-1, None)

        if current:
            self.cmds[idx] = cmd
        else:
            self.cmds.append(cmd)

    def optimize_geo(self):
        setbits = 0
        clearbits = 0

        # we'll remove all the setgeo and cleargeo cmds, and keep the others
        new_cmds = []
        for idx, cmd in enumerate(self.cmds):
            bits = int.from_bytes(cmd[4:], 'big')
            if cmd[0] == G_SETGEOMETRYMODE:
                setbits |= bits
                clearbits &= ~bits
                # print(f'  S {setbits:04X} C {clearbits:04X}')
            elif cmd[0] == G_CLEARGEOMETRYMODE:
                setbits &= ~bits
                clearbits |= bits
                # print(f'  C {clearbits:04X} S {setbits:04X}')
            else:
                new_cmds.append(cmd)

        # setgeo and cleargeo commands cancel each other, if they affect the same bits
        if setbits != 0:
            cmd = bytearray([G_SETGEOMETRYMODE] + [0x00]*3)
            cmd += setbits.to_bytes(4, 'big')
            new_cmds.append(cmd)

        if clearbits != 0:
            cmd = bytearray([G_CLEARGEOMETRYMODE] + [0x00]*3)
            cmd += clearbits.to_bytes(4, 'big')
            new_cmds.append(cmd)

        self.cmds = new_cmds

    def optimize_otherH(self):
        otherHs = []
        copycmds = self.cmds[:]
        for cmd in reversed(copycmds):
            if cmd in otherHs:
                self.cmds.remove(cmd)
            else:
                otherHs.append(cmd)

    def optimize_texconfig(self):
        texfound = False
        copycmds = self.cmds[:]
        for cmd in reversed(copycmds):
            if cmd[0] == G_TEXTURE:
                if texfound:
                    self.cmds.remove(cmd)
                texfound = True

    def optimize_cmds(self):
        if self.optimized: return

        self.optimize_geo()
        self.optimize_otherH()
        self.optimize_texconfig()
        self.optimized = True

    def has_envmap(self):
        return bool(self.geom_mode & (G_LIGHTING | G_TEXTURE_GEN))

    # returns a ID for this setup, based on the commands/texture id etc
    def id(self):
        mat_id = 'Mat'
        if self.has_texture():
            mat_id += f'-{self.texnum:04X}'

        if len(self.cmds): mat_id += '-'

        for cmd in self.cmds:
            mat_id += f'{cmd[0]:02X}'

        mat_id += f'.{self.mesh_idx:02X}'

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
    if fmt == G_IM_FMT_RGBA: return True

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
    if not cmds: return

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

        cmdstr = ''.join(f'{b:02X}' for b in cmd)
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
    name = matsetup.id()
    # if there is already a material for this texture/mode, don't create a new one
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    has_envmap = matsetup.has_envmap()
    preset = 'ENV_MAPPING' if has_envmap else 'DIFFUSE'
    mat = material_from_template(name, preset)

    node_tex = mat.node_tree.nodes['teximage']
    node_bsdf = mat.node_tree.nodes['p_bsdf']
    node_vtxcolor = mat.node_tree.nodes['vtxcolor']
    node_vtxcolor.layer_name = 'vtxcolor'

    texnum = matsetup.texnum & 0xffffff
    img = f'{texnum:04X}.png'
    imglib = bpy.data.images
    node_tex.image = imglib[img]
    node_tex.extension = tex_smode(matsetup.smode)

    if use_alpha:
        mat.node_tree.links.new(node_bsdf.inputs['Alpha'], node_tex.outputs['Alpha'])

    material_setup_cmds(mat.node_tree, matsetup)

    if bpy.app.version < (4, 0, 0) and use_alpha and not material_has_lighting(mat):
        mat.blend_method = 'BLEND'

    mat['has_envmap'] = has_envmap

    return mat

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
        addon_path = pdu.addon_path()
        blend_file = MAT_BLENDFILE_4X if bpy.app.version >= (4, 0, 0) else MAT_BLENDFILE_3X
        with bpy.data.libraries.load(f'{addon_path}/{blend_file}') as (data_from, data_to):
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

def material_cmds(mat, geobits):
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

PORTAL_MAT = 'PD_PortalMat'
WAYPOINT_MAT = 'PD_WaypointMat'

def create_basic_material(name, color = None, alpha = 0):
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

    links.new(node_pbsdf.outputs['BSDF'], node_output.inputs['Surface'])
    # newmat.surface_render_method = 'BLENDED'
    return newmat

def portal_material():
    return create_basic_material(PORTAL_MAT)

def waypoint_material():
    return create_basic_material(WAYPOINT_MAT, (0.0, 0.8, 0.0, 1.0), 1.0)
