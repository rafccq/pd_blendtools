import bpy
from bpy.props import (
    PointerProperty, BoolProperty
)
from bpy.types import SpaceNodeEditor, PropertyGroup

from nodes.nodeutils import *


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

    def on_update(self, _context):
        s, t = self.get_texscale()

        b = self.tile_index | (self.max_lods << 3)
        self.cmd = f'BB00{b:02X}01{s:04X}{t:04X}'

    tex_scale: bpy.props.FloatVectorProperty(
        name='tex_scale',
        min=0,
        max=1,
        size=2,
        default=(1, 1),
        step=1,
        update=on_update,
    )

    tile_index: bpy.props.IntProperty(name='tile_index', default=0, min=0, max=7, update=on_update)
    max_lods: bpy.props.IntProperty(name='max_lods', default=0, min=0, max=7, update=on_update)

def mat_tex_set(texload, cmd):
    s = (cmd & 0x0f00) >> 8
    t = (cmd & 0xf000) >> 12

    if s == 0xffff or t == 0xffff:
        texload.autoscale = True
    else:
        texload.tex_scale[0] = s / 2**16
        texload.tex_scale[1] = t / 2**16

    w0 = (cmd & 0xffffffff00000000) >> 32
    b = (w0 & 0xff00) >> 8
    texload.tile_index = b & 0x7
    texload.max_lods = (b & 0x38) >> 3

def draw_buttons(texload, context, layout):
    col = layout.column()
    col.prop(texload, 'autoscale', text='Auto Scale')

    row = col.row()
    row.prop(texload, 'tex_scale', text='')

    row.enabled = not texload.autoscale

    col.prop(texload, 'tile_index')
    col.prop(texload, 'max_lods')

def get_cmd(self):
    s, t = self.get_texscale()
    if self.autoscale: s = t = 0xFFFF
    return f'{self.cmd[:8]}{s:04X}{t:04X}'

TEX_WRAPMODES = [
    ('wrap', 'Wrap', 0),
    ('clamp', 'Clamp', 1),
    ('mirror', 'Mirror', 2),
]

class MatTexLoad(PropertyGroup):
    def on_update(self, context):
        img = '0' + self.cmd[13:]
        if self.image:
            img = self.image.name.replace('.png', '')

        smode = self.enum_value('smode')
        tmode = self.enum_value('tmode')
        offset = 2 if self.offset else 0
        shifts = self.shift_s
        shiftt = self.shift_t

        w0 = (0xc0 << 24) | (smode << 22) | (tmode << 20) | (offset << 18) | \
             (shifts << 14) | (shiftt << 10) | (self.lod_flag << 9) | self.subcmd

        self.cmd = f'{w0:08X}0000{img}'

        if type(context.space_data) is not SpaceNodeEditor: return

        # sync the material's teximage with this node's texture
        tree = context.space_data.node_tree
        node_tex = tree.nodes['teximage']
        imglib = bpy.data.images
        node_tex.image = imglib[self.image.name]


    image: PointerProperty(name='image', type=bpy.types.Image, update=on_update)
    smode: make_prop('smode', {'smode': TEX_WRAPMODES}, 'wrap', on_update)
    tmode: make_prop('tmode', {'tmode': TEX_WRAPMODES}, 'wrap', on_update)
    lod_flag: BoolProperty(name='lod_flag', default=False, description='Write LOD', update=on_update)
    offset: BoolProperty(name='offset', default=True, description='Offset', update=on_update)

    shift_s: bpy.props.IntProperty(name='shift_s', default=0, min=0, max=15, update=on_update)
    shift_t: bpy.props.IntProperty(name='shift_t', default=0, min=0, max=15, update=on_update)
    subcmd: bpy.props.IntProperty(name='subcmd', default=0, min=0, max=4, update=on_update)

def mat_texconfig_set(texconfig):
    w0 = (cmd & 0xffffffff00000000) >> 32

    texconfig.smode = item_from_value(TEX_WRAPMODES, (w0 >> 22) & 0x3)
    texconfig.tmode = item_from_value(TEX_WRAPMODES, (w0 >> 20) & 0x3)
    texconfig.offset = bool((w0 >> 18) & 0x3)
    texconfig.shift_s = (w0 >> 14) & 0xf
    texconfig.shift_t = (w0 >> 10) & 0xf
    texconfig.lod_flag = bool(w0 & 0x200)
    texconfig.subcmd = w0 & 0x7
    img = texconfig.cmd[12:]
    img = cmd & 0xf00

    if img != 0:
        texconfig.image = bpy.data.images[f'{img}.png']

def draw_buttons(texconfig, context, layout):
    layout.prop(texconfig, 'image', text='')
    layout.prop(texconfig, 'smode')
    layout.prop(texconfig, 'tmode')
    layout.prop(texconfig, 'subcmd')
    layout.prop(texconfig, 'shift_s')
    layout.prop(texconfig, 'shift_t')
    layout.prop(texconfig, 'lod_flag')
    layout.prop(texconfig, 'offset')
