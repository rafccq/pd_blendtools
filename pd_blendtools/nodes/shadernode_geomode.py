from bpy.props import BoolProperty

from .shadernode_base import PD_ShaderNodeBase
from pd_data.gbi import *
from utils import pd_utils as pdu

DESC_GEO_ZBUFFER = 'ZBuffer description'
DESC_GEO_SHADE = 'Shade description'
DESC_GEO_CULL_FRONT = 'Cull front description'
DESC_GEO_CULL_BACK = 'Cull back description'
DESC_GEO_LIGHTING = 'Lighting description'
DESC_GEO_TEXTURE_GEN = 'Texture gen description'
DESC_GEO_TEXTURE_GEN_LINEAR = 'Texture gen linear description'
DESC_GEO_SHADING_SMOOTH = 'Shading smooth description'

GEO_FLAGS = {
    'g_zbuffer':            G_ZBUFFER,
    'g_shade':              G_SHADE,
    'g_cull_front':         G_CULL_FRONT,
    'g_cull_back':          G_CULL_BACK,
    'g_lighting':           G_LIGHTING,
    'g_texture_gen':        G_TEXTURE_GEN,
    'g_texture_gen_linear': G_TEXTURE_GEN_LINEAR,
    'g_shading_smooth':     G_SHADING_SMOOTH,
}

class PD_ShaderNodeSetGeoMode(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.setgeometrymode'
    bl_label = "Set Geo Mode"
    bl_icon = 'MESH_DATA'

    opcode = 0xB7

    def on_update(self, _context):
        mode_bits = 0
        for flag, bits in GEO_FLAGS.items():
            mode_bits |= bits if getattr(self, flag) else 0

        self.cmd = f'{self.opcode:02X}000000{mode_bits:08X}'

    hide: BoolProperty(name='Hide fields', default=False, description='Hide fields (still accessible in the panel)')

    g_zbuffer: BoolProperty(name='g_zbuffer', update=on_update, default=False, description=DESC_GEO_ZBUFFER)
    g_shade: BoolProperty(name='g_shade', update=on_update, default=False, description=DESC_GEO_SHADE)
    g_cull_front: BoolProperty(name='g_cull_front', update=on_update, default=False, description=DESC_GEO_CULL_FRONT)
    g_cull_back: BoolProperty(name='g_cull_back', update=on_update, default=False, description=DESC_GEO_CULL_BACK)
    g_lighting: BoolProperty(name='g_lighting', update=on_update, default=False, description=DESC_GEO_LIGHTING)
    g_texture_gen: BoolProperty(name='g_texture_gen', update=on_update, default=False, description=DESC_GEO_TEXTURE_GEN)
    g_texture_gen_linear: BoolProperty(name='g_texture_gen_linear', update=on_update, default=False, description=DESC_GEO_TEXTURE_GEN_LINEAR)
    g_shading_smooth: BoolProperty(name='g_shading_smooth', update=on_update, default=False, description=DESC_GEO_SHADING_SMOOTH)

    def init(self, _context):
        self.cmd = 'B700000000060000'
        self.pd_init()

    def update_ui(self):
        cmd = int(f'0x{self.cmd}', 16)
        for flag, bits in GEO_FLAGS.items():
            setattr(self, flag, bool(cmd & bits))

    def draw_props(self, _context, layout):
        col: UILayout = layout.column(align=True)
        for flag, _ in GEO_FLAGS.items():
            col.prop(self, flag)

    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)

        col: UILayout = layout.column(align=True)
        col.prop(self, 'hide')
        if not self.hide:
            pdu.ui_separator(col, type='LINE')
            self.draw_props(context, col)

    def draw_buttons_ext(self, context, layout):
        self.draw_props(context, layout)


class PD_ShaderNodeClearGeoMode(PD_ShaderNodeSetGeoMode):
    bl_idname = 'pd.nodes.cleargeometrymode'
    bl_label = "Clear Geo Mode"
    bl_icon = 'MESH_DATA'

    opcode = 0xB6

