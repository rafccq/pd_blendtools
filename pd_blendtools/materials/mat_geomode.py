from bpy.types import UILayout, PropertyGroup
from bpy.props import BoolProperty

from pd_data.gbi import *
from nodes.nodeutils import make_prop, item_from_value
from utils import pd_utils as pdu

from fast64.f3d import prop_split


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
    'g_tex_gen':            G_TEXTURE_GEN,
    'g_tex_gen_linear':     G_TEXTURE_GEN_LINEAR,
    'g_shade_smooth':       G_SHADING_SMOOTH,
}

class MatGeoMode(PropertyGroup):
    opcode = 0xB7

    def on_update(self, _context):
        mode_bits = 0
        for flag, bits in GEO_FLAGS.items():
            mode_bits |= bits if getattr(self, flag) else 0

        # self.cmd = f'{self.opcode:02X}000000{mode_bits:08X}'

    hide: BoolProperty(name='Hide fields', default=False, description='Hide fields (still accessible in the panel)')

    g_zbuffer: BoolProperty(name='Z Buffer', update=on_update, default=False, description=DESC_GEO_ZBUFFER)
    g_shade: BoolProperty(name='Shading', update=on_update, default=False, description=DESC_GEO_SHADE)
    g_cull_front: BoolProperty(name='Cull Front', update=on_update, default=False, description=DESC_GEO_CULL_FRONT)
    g_cull_back: BoolProperty(name='Cull Back', update=on_update, default=False, description=DESC_GEO_CULL_BACK)
    g_lighting: BoolProperty(name='Lighting', update=on_update, default=False, description=DESC_GEO_LIGHTING)
    g_tex_gen: BoolProperty(name='Texture UV Generate', update=on_update, default=False, description=DESC_GEO_TEXTURE_GEN)
    g_tex_gen_linear: BoolProperty(name='Texture UV Generate Linear', update=on_update, default=False, description=DESC_GEO_TEXTURE_GEN_LINEAR)
    g_shade_smooth: BoolProperty(name='Shading Smooth', update=on_update, default=False, description=DESC_GEO_SHADING_SMOOTH)

def ident(parent, settings, text_or_prop, is_text=False):
    c = parent.column(align=True)
    if is_text:
        c.label(text=text_or_prop)
        enable = True
    else:
        c.prop(settings, text_or_prop)
        enable = getattr(settings, text_or_prop)
    c = c.split(factor=0.1)
    c.label(text="")
    c = c.column(align=True)
    c.enabled = enable
    return c

def matgeo_draw(geomode, layout, _context):
    col: UILayout = layout.column(align=True)
    col.prop(geomode, 'g_shade_smooth')
    c = ident(col, geomode, 'g_lighting')
    c = ident(c, geomode, 'g_tex_gen')
    c.prop(geomode, 'g_tex_gen_linear')
    c = ident(col, geomode, 'Face Culling:', True)
    c.prop(geomode, 'g_cull_front')
    c.prop(geomode, 'g_cull_back')
    c = ident(col, geomode, 'Disable if not using:', True)
    c.prop(geomode, 'g_zbuffer')
    c.prop(geomode, 'g_shade')

def matgeo_set(geomode, cmd):
    for flag, bits in GEO_FLAGS.items():
        setattr(geomode, flag, bool(cmd & bits))
