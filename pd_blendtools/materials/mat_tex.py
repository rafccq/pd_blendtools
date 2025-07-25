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
    node_tex.image = texload.image
    node_tex.extension = modemap[texload.smode]

class MatTexLoad(PropertyGroup):
    def on_update(self, context):
        mat = get_material_from_context(context)
        if not mat: return

        img_update_nodes(mat)

    image: PointerProperty(name='image', type=bpy.types.Image, update=on_update)
    smode: make_prop('smode', {'smode': TEX_WRAPMODES}, 'wrap', on_update)
    tmode: make_prop('tmode', {'tmode': TEX_WRAPMODES}, 'wrap', on_update)
    lod_flag: BoolProperty(name='lod_flag', default=False, description='Write LOD', update=on_update)
    offset: BoolProperty(name='offset', default=True, description='Offset', update=on_update)

    shift_s: bpy.props.IntProperty(name='shift_s', default=0, min=0, max=15, update=on_update)
    shift_t: bpy.props.IntProperty(name='shift_t', default=0, min=0, max=15, update=on_update)
    subcmd: bpy.props.IntProperty(name='subcmd', default=0, min=0, max=4, update=on_update)

    menu: BoolProperty(name='menu', default=False, description='Texture Params', update=on_update)
    autoprop: BoolProperty(name='autoprop', default=False, description='Auto Set Other Properties')
    enabled: BoolProperty(name='enabled', default=False, description='Texture Enabled')

def mat_texload_set(texload, cmd):
    w0 = (cmd & 0xffffffff00000000) >> 32

    texload.smode = item_from_value(TEX_WRAPMODES, (w0 >> 22) & 0x3)
    texload.tmode = item_from_value(TEX_WRAPMODES, (w0 >> 20) & 0x3)
    texload.offset = bool((w0 >> 18) & 0x3)
    texload.shift_s = (w0 >> 14) & 0xf
    texload.shift_t = (w0 >> 10) & 0xf
    texload.lod_flag = bool(w0 & 0x200)
    texload.subcmd = w0 & 0x7
    img = cmd & 0x0fff

    if img != 0:
        texload.image = bpy.data.images[f'{img:04X}.png']

def mat_texload_draw(texload, layout, context):
    layout.prop(texload, 'enabled', text='Set Texture')

    layout = layout.column()
    layout.enabled = texload.enabled

    layout.template_ID(
        texload, "image", new="image.new", open="image.open", unlink="pdtools.tex0_unlink"
    )

    prop_split(layout, texload, 'smode', 'S Mode')
    prop_split(layout, texload, 'tmode', 'T Mode')

    layout.prop(texload, 'autoprop', text='Auto Set Other Properties')
    if not texload.autoprop:
        prop_split(layout, texload, 'shift_s', 'Shift S')
        prop_split(layout, texload, 'shift_t', 'Shift T')

        prop_split(layout, texload, 'lod_flag', 'LOD Flag')
        prop_split(layout, texload, 'offset', 'Offset')
        prop_split(layout, texload, 'subcmd', 'Sub Command')

def mat_tex_draw(pd_mat, layout, context):
    texload = pd_mat.texload

    col = layout.column()
    col.prop(texload, 'menu', text = 'Texture 0 Properties+', icon = 'TRIA_DOWN' if texload.menu else 'TRIA_RIGHT')
    if texload.menu:
        mat_texload_draw(texload, col, context)
        
    texconfig = pd_mat.texconfig
    box = col.box()
    mat_texconfig_draw(texconfig, box, context)

def texload_command(texload):
    img = int(texload.image.name.replace('.png', ''), 16)

    smode = pdu.enum_value(texload, 'smode')
    tmode = pdu.enum_value(texload, 'tmode')
    offset = 2 if texload.offset else 0
    shifts = texload.shift_s
    shiftt = texload.shift_t

    w0 = (0xc0 << 24) | (smode << 22) | (tmode << 20) | (offset << 18) | \
         (shifts << 14) | (shiftt << 10) | (texload.lod_flag << 9) | texload.subcmd

    return (w0 << 8*4) | (img & 0xffff)
