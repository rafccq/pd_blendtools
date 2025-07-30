import bpy
from bpy.props import (
    PointerProperty, BoolProperty
)
from bpy.types import SpaceNodeEditor, PropertyGroup

from nodes.nodeutils import *
from utils import pd_utils as pdu

from fast64.utility import prop_split, get_material_from_context


class MatSetTImage(PropertyGroup):
    def init(self, _context):
        self.pd_init()

    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)
        row = layout.row()
        row.label(text=f'IMG: {self.cmd[8:]}')


class MatTexConfig(PropertyGroup):
    bl_idname = 'pd.nodes.textureconfig'
    bl_label = "TextureConfig"
    bl_icon = 'TEXTURE'

    autoscale: BoolProperty(name='Auto Scale', default=False)

    def get_texscale(self):
        s=self.tex_scale[0]
        t=self.tex_scale[1]

        s = int(self.tex_scale[0] * 2**16) if s != 1.0 else 0xFFFF
        t = int(self.tex_scale[1] * 2**16) if t != 1.0 else 0xFFFF
        return s, t

    tex_scale: bpy.props.FloatVectorProperty(
        name='tex_scale',
        min=0,
        max=1,
        size=2,
        default=(1, 1),
        step=1,
    )

    tile_index: bpy.props.IntProperty(name='tile_index', default=0, min=0, max=7)
    max_lods: bpy.props.IntProperty(name='max_lods', default=0, min=0, max=7)

def mat_texconfig_set(texconfig, cmd):
    s = (cmd & 0xffff00) >> 8
    t = (cmd & 0xffff000) >> 12

    if s == 0xffff or t == 0xffff:
        texconfig.autoscale = True
    else:
        texconfig.tex_scale[0] = s / 2 ** 16
        texconfig.tex_scale[1] = t / 2 ** 16

    w0 = (cmd & 0xffffffff00000000) >> 32
    b = (w0 & 0xff00) >> 8
    texconfig.tile_index = b & 0x7
    texconfig.max_lods = (b & 0x38) >> 3

def mat_texconfig_draw(texconfig, layout, context):
    col = layout.column()
    col.prop(texconfig, 'autoscale', text='Auto Scale')

    row = col.row()
    row.prop(texconfig, 'tex_scale', text='')

    row.enabled = not texconfig.autoscale

    prop_split(col, texconfig, 'tile_index', 'Tile Index')
    prop_split(col, texconfig, 'max_lods', 'Max LODs')

def get_cmd(self):
    s, t = self.get_texscale()
    if self.autoscale: s = t = 0xFFFF
    return f'{self.cmd[:8]}{s:04X}{t:04X}'

TEX_WRAPMODES = [
    ('wrap', 'Wrap', 0),
    ('clamp', 'Clamp', 1),
    ('mirror', 'Mirror', 2),
]

def img_update_nodes(mat):
    tree = mat.node_tree
    texload = mat.pd_mat.texload
    node_tex = tree.nodes['teximage']

    modemap = {'wrap': 'REPEAT', 'clamp': 'EXTEND', 'mirror': 'MIRROR'}
    node_tex.image = texload.tex0
    node_tex.extension = modemap[texload.smode]

class MatTexLoad(PropertyGroup):
    def on_update(self, context):
        mat = get_material_from_context(context)
        if not mat: return

        img_update_nodes(mat)

    tex0: PointerProperty(name='tex0', type=bpy.types.Image, update=on_update)
    tex1: PointerProperty(name='tex1', type=bpy.types.Image)
    smode: make_prop('smode', {'smode': TEX_WRAPMODES}, 'wrap', on_update)
    tmode: make_prop('tmode', {'tmode': TEX_WRAPMODES}, 'wrap', on_update)
    lod_flag: BoolProperty(name='lod_flag', default=False, description='Write LOD')
    offset: BoolProperty(name='offset', default=True, description='Offset')

    shift_s: bpy.props.IntProperty(name='shift_s', default=0, min=0, max=15)
    shift_t: bpy.props.IntProperty(name='shift_t', default=0, min=0, max=15)
    subcmd: bpy.props.IntProperty(name='subcmd', default=0, min=0, max=4, update=on_update)

    menu0: BoolProperty(name='menu0', default=False, description='Texture Params')
    menu1: BoolProperty(name='menu1', default=False, description='Texture Params')
    tex_set: BoolProperty(name='tex_set', default=False, description='Texture Enabled')

def mat_texload_set(texload, cmd):
    w0 = (cmd & 0xffffffff00000000) >> 32

    texload.smode = item_from_value(TEX_WRAPMODES, (w0 >> 22) & 0x3)
    texload.tmode = item_from_value(TEX_WRAPMODES, (w0 >> 20) & 0x3)
    texload.offset = bool((w0 >> 18) & 0x3)
    texload.shift_s = (w0 >> 14) & 0xf
    texload.shift_t = (w0 >> 10) & 0xf
    texload.lod_flag = bool(w0 & 0x200)
    texload.subcmd = w0 & 0x7

    imglib = bpy.data.images
    tex0 = cmd & 0x0fff

    if tex0:
        texload.tex0 = imglib[f'{tex0:04X}.png']
        texload.tex_set = True

    tex1 = (cmd >> 4*3) & 0xfff
    if tex1:
        texload.tex1 = imglib[f'{tex1:04X}.png']

def mat_settimg_set(texload, cmd):
    texnum = cmd & 0xffff
    texname = f'{texnum:04X}.png'

    imglib = bpy.data.images

    texload.tex0 = imglib[texname]
    texload.tex_set = True

def mat_texload_draw(texload, idx, layout, context):
    layout = layout.column()
    layout.enabled = texload.tex_set

    layout.template_ID(
        texload, f'tex{idx}', new="image.new", open="image.open", unlink=f"pdtools.tex{idx}_unlink"
    )

    if idx == 0:
        layout.prop(texload, 'tex_set', text='Set Texture')
        prop_split(layout, texload, 'smode', 'S Mode')
        prop_split(layout, texload, 'tmode', 'T Mode')
        prop_split(layout, texload, 'lod_flag', 'LOD Flag')
        prop_split(layout, texload, 'offset', 'Offset')
        prop_split(layout, texload, 'subcmd', 'Sub Command')

    if idx == 1:
        prop_split(layout, texload, 'shift_s', 'Shift S')
        prop_split(layout, texload, 'shift_t', 'Shift T')

def mat_tex_draw(pd_mat, layout, context):
    texload = pd_mat.texload

    col = layout.column()
    col.prop(texload, 'menu0', text = 'Texture 0 Properties', icon = 'TRIA_DOWN' if texload.menu0 else 'TRIA_RIGHT')
    if texload.menu0:
        mat_texload_draw(texload, 0, col, context)

    if texload.subcmd == 1:
        col.prop(texload, 'menu1', text='Texture 1 Properties', icon='TRIA_DOWN' if texload.menu1 else 'TRIA_RIGHT')
        if texload.menu1:
            mat_texload_draw(texload, 1, col, context)

    texconfig = pd_mat.texconfig
    pdu.ui_separator(col, type='SPACE')
    box = col.box()
    mat_texconfig_draw(texconfig, box, context)

def texload_command(texload):
    tex0 = int(texload.tex0.name.replace('.png', ''), 16)
    teximg1 = texload.tex1
    tex1 = int(teximg1.name.replace('.png', ''), 16) if teximg1 else 0

    smode = pdu.enum_value(texload, 'smode')
    tmode = pdu.enum_value(texload, 'tmode')
    offset = 2 if texload.offset else 0
    shifts = texload.shift_s
    shiftt = texload.shift_t
    minlv = 0xf8 if tex1 else 0 # min level fixed at F8 for now (TODO check)

    w0 = (0xc0 << 24) | (smode << 22) | (tmode << 20) | (offset << 18) | \
         (shifts << 14) | (shiftt << 10) | (texload.lod_flag << 9) | texload.subcmd

    return (w0 << 8*4) | (minlv << 4*6) | (tex1 << 4*3) | (tex0 & 0xfff)
