import bpy
from nodes.nodeutils import make_prop, item_from_value

from .shadernode_base import PD_ShaderNodeBase
from bpy.props import (
    PointerProperty, EnumProperty, FloatProperty, BoolProperty
)

class PD_ShaderNodeTexConfig(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.textureconfig'
    bl_label = "TextureConfig"
    bl_icon = 'TEXTURE'

    autoscale: BoolProperty(name='Auto Scale', default=False)

    def on_update(self, context):
        s=self.tex_scale[0]
        t=self.tex_scale[1]

        s = int(self.tex_scale[0] * 2**16) if s != 1.0 else 0xFFFF
        t = int(self.tex_scale[1] * 2**16) if t != 1.0 else 0xFFFF

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

    def init(self, context):
        self.pd_init()

    def update_ui(self):
        s = int(self.cmd[8:12], 16)
        t = int(self.cmd[12:], 16)

        if s == 0xffff or t == 0xffff:
            self.autoscale = True
        else:
            self.tex_scale[0] = s / 2**16
            self.tex_scale[1] = t / 2**16

        w0 = int(f'0x{self.cmd[:8]}', 16)
        b = (w0 & 0xff00) >> 8
        self.tile_index = b & 0x7
        self.max_lods = (b & 0x38) >> 3

    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)
        col = layout.column()
        col.prop(self, 'autoscale', text='Auto Scale')

        row = col.row()
        row.prop(self, 'tex_scale', text='')

        row.enabled = not self.autoscale

        col.prop(self, 'tile_index')
        col.prop(self, 'max_lods')

TEX_WRAPMODES = [
    ('wrap', 'Wrap', 0),
    ('clamp', 'Clamp', 1),
    ('mirror', 'Mirror', 2),
]

class PD_ShaderNodeTexLoad(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.textureload'
    bl_label = "TextureLoad"
    bl_icon = 'TEXTURE'

    def on_update(self, context):
        img = self.cmd[12:]
        if self.image:
            img = self.image.name.replace('.bmp', '')

        smode = self.enum_value('smode')
        tmode = self.enum_value('tmode')
        offset = 2 if self.offset else 0
        shifts = self.shift_s
        shiftt = self.shift_t

        w0 = (0xc0 << 24) | (smode << 22) | (tmode << 20) | (offset << 18) | \
             (shifts << 14) | (shiftt << 10) | (self.lod_flag << 9) | self.subcmd

        self.cmd = f'{w0:08X}0000{img}'


    image: PointerProperty(name='image', type=bpy.types.Image, update=on_update)
    smode: make_prop('smode', {'smode': TEX_WRAPMODES}, 'wrap', on_update)
    tmode: make_prop('tmode', {'tmode': TEX_WRAPMODES}, 'wrap', on_update)
    lod_flag: BoolProperty(name='lod_flag', default=False, description='Write LOD', update=on_update)
    offset: BoolProperty(name='offset', default=True, description='Offset', update=on_update)

    shift_s: bpy.props.IntProperty(name='shift_s', default=0, min=0, max=15, update=on_update)
    shift_t: bpy.props.IntProperty(name='shift_t', default=0, min=0, max=15, update=on_update)
    subcmd: bpy.props.IntProperty(name='subcmd', default=0, min=0, max=4, update=on_update)

    def init(self, context):
        self.pd_init()

    def update_ui(self):
        w0 = int(f'0x{self.cmd[:8]}', 16)

        self.smode = item_from_value(TEX_WRAPMODES, (w0 >> 22) & 0x3)
        self.tmode = item_from_value(TEX_WRAPMODES, (w0 >> 20) & 0x3)
        self.offset = bool((w0 >> 18) & 0x3)
        self.shift_s = (w0 >> 14) & 0xf
        self.shift_t = (w0 >> 10) & 0xf
        self.lod_flag = bool(w0 & 0x200)
        self.subcmd = w0 & 0x7
        img = self.cmd[12:]

        if img != '0000':
            self.image = bpy.data.images[f'{img}.bmp']

    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)
        layout.prop(self, 'image', text='')
        layout.prop(self, 'smode')
        layout.prop(self, 'tmode')
        layout.prop(self, 'subcmd')
        layout.prop(self, 'shift_s')
        layout.prop(self, 'shift_t')
        layout.prop(self, 'lod_flag')
        layout.prop(self, 'offset')
