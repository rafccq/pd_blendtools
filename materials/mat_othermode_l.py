from bpy.props import (
    BoolProperty, EnumProperty, IntProperty
)
from bpy.types import UILayout, PropertyGroup
from utils import pd_utils as pdu

from fast64.utility import prop_split
from fast64.f3d import f3d_enums

ENUM_ALPHACMP = f3d_enums.enumAlphaCompare
ENUM_DEPTHSRC = f3d_enums.enumDepthSource

DESC_ALPHACMP = f3d_enums.DESC_ALPHACMP
DESC_DEPTHSRC = f3d_enums.DESC_DEPTHSRC

NOT_SET = f3d_enums.NOT_SET


LOWER_ALPHACOMP = [
    ('None', 'None description',         0b00),
    ('Treshold', 'Treshold description', 0b01),
    ('Dither', 'Dither description',     0b11),
    ('[Not Set]', 'Not Set',             0xff),
]

LOWER_ZSOURCE = [
    ('Pixel', 'Pixel description',         0),
    ('Primitive', 'Primitive description', 1),
    ('[Not Set]', 'Not Set',            0xff),
]

LOWER_RENDERMODECI_FLAGS = {
    'aa_en':         ('Antialiasing',      1 << 0),
    'z_cmp':         ('Z Testing',         1 << 1),
    'z_upd':         ('Z Writing',         1 << 2),
    'im_rd':         ('IM_RD (?)',         1 << 3),
    'clr_on_cvg':    ('Color on Coverage', 1 << 4),
    'cvg_x_alpha':   ('Coverage x Alpha',  1 << 9),
    'alpha_cvg_sel': ('Coverage <> alpha', 1 << 10),
    'force_bl':      ('Force Blending',    1 << 11),
}

# cycle independent params
LOWER_RENDERMODECI_CVGDST = [
    ('Clamp', 'Clamp', 0),
    ('Wrap',  'Wrap',  1),
    ('Full',  'Full',  2),
    ('Save',  'Save',  3),
]

LOWER_RENDERMODECI_ZMODE = [
    ('Opaque',            'Opaque',             0),
    ('Interpenetrating',  'Interpenetrating',   1),
    ('Translucent (XLU)', 'Translucent (XLU)',  2),
    ('Decal',             'Decal',              3),
]

# cycle dependent params for the formula: (P * A + M - B) / (A + B)
LOWER_RENDERMODECD_BLENDCOLOR = [
    ('Input (CC/Blender)',  'Input (CC/Blender)', 0),
    ('Framebuffer Color', 'Framebuffer Color', 1),
    ('Blend Color',  'Blend Color', 2),
    ('Fog Color', 'Fog Color', 3),
]

LOWER_RENDERMODECD_BLENDALPHA = [
    ('Color Combiner Alpha',    'Color Combiner Alpha', 0),
    ('Fog Alpha',   'Fog Alpha', 1),
    ('Shade Alpha', 'Shade Alpha', 2),
    ('0', '0', 3),
]

LOWER_RENDERMODECD_BLENDMIX = [
    ('1 - A', '1 - A', 0),
    ('Framebuffer Alpha', 'Framebuffer Alpha', 1),
    ('1', '1', 2),
    ('0', '0', 3),
]

LOWER_RENDERMODECD_ITEMS = {
    'blend_b1': LOWER_RENDERMODECD_BLENDMIX,
    'blend_b2': LOWER_RENDERMODECD_BLENDMIX,

    'blend_m1': LOWER_RENDERMODECD_BLENDCOLOR,
    'blend_m2': LOWER_RENDERMODECD_BLENDCOLOR,

    'blend_a1': LOWER_RENDERMODECD_BLENDALPHA,
    'blend_a2': LOWER_RENDERMODECD_BLENDALPHA,

    'blend_p1': LOWER_RENDERMODECD_BLENDCOLOR,
    'blend_p2': LOWER_RENDERMODECD_BLENDCOLOR,
}

MODE_ALPHACMP   = 0
MODE_ZSRC       = 2
MODE_RENDERMODE = 3

LOWER_MODES = [
    ('g_mdsft_alpha_compare', 'Alpha Compare',      MODE_ALPHACMP),
    ('g_mdsft_zsrcsel',       'Z Source Selection', MODE_ZSRC),
    ('rendermode',            'Render Mode',        MODE_RENDERMODE),
]

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

DESC_LOWER_AA_EN         = 'AA_EN description'
DESC_LOWER_Z_CMP         = 'Z_CMP description'
DESC_LOWER_Z_UPD         = 'Z_UPD description'
DESC_LOWER_IM_RD         = 'IM_RD description'
DESC_LOWER_CLR_ON_CVG    = 'CLR_ON_CVG description'
DESC_LOWER_CVG_X_ALPHA   = 'CVG_X_ALPHA description'
DESC_LOWER_ALPHA_CVG_SEL = 'ALPHA_CVG_SEL description'
DESC_LOWER_FORCE_BL      = 'FORCE_BL description'

class MatOtherModeL(PropertyGroup):
    g_mdsft_alpha_compare: EnumProperty( name="Alpha Compare", items=ENUM_ALPHACMP, default=NOT_SET[0], description=DESC_ALPHACMP)
    g_mdsft_zsrcsel: EnumProperty( name="Depth Source", items=ENUM_DEPTHSRC, default=NOT_SET[0], description=DESC_DEPTHSRC)

    set_rendermode: BoolProperty(name='set_rendermode', default=False)

    aa_en: BoolProperty(name='aa_en', default=False, description=DESC_LOWER_AA_EN)
    z_cmp: BoolProperty(name='z_cmp', default=False, description=DESC_LOWER_Z_CMP)
    z_upd: BoolProperty(name='z_upd', default=False, description=DESC_LOWER_Z_UPD)
    im_rd: BoolProperty(name='im_rd', default=False, description=DESC_LOWER_IM_RD)
    clr_on_cvg: BoolProperty(name='clr_on_cvg', default=False, description=DESC_LOWER_CLR_ON_CVG)
    cvg_x_alpha: BoolProperty(name='cvg_x_alpha', default=False, description=DESC_LOWER_CVG_X_ALPHA)
    alpha_cvg_sel: BoolProperty(name='alpha_cvg_sel', default=False, description=DESC_LOWER_ALPHA_CVG_SEL)
    force_bl: BoolProperty(name='force_bl', default=False, description=DESC_LOWER_FORCE_BL)

    # cycle independent props
    cvg_dst: pdu.make_prop('cvg_dst', {'cvg_dst': LOWER_RENDERMODECI_CVGDST}, 'clamp')
    zmode: pdu.make_prop('zmode', {'zmode': LOWER_RENDERMODECI_ZMODE}, 'opaque')

    # cycle dependent props cycle 1
    blend_b1: pdu.make_prop('blend_b1', LOWER_RENDERMODECD_ITEMS, pdu.make_id(LOWER_RENDERMODECD_BLENDMIX[0][0]))
    blend_m1: pdu.make_prop('blend_m1', LOWER_RENDERMODECD_ITEMS, pdu.make_id(LOWER_RENDERMODECD_BLENDCOLOR[0][0]))
    blend_a1: pdu.make_prop('blend_a1', LOWER_RENDERMODECD_ITEMS, pdu.make_id(LOWER_RENDERMODECD_BLENDALPHA[0][0]))
    blend_p1: pdu.make_prop('blend_p1', LOWER_RENDERMODECD_ITEMS, pdu.make_id(LOWER_RENDERMODECD_BLENDCOLOR[0][0]))

    # cycle dependent props cycle 2
    blend_b2: pdu.make_prop('blend_b2', LOWER_RENDERMODECD_ITEMS, pdu.make_id(LOWER_RENDERMODECD_BLENDMIX[0][0]))
    blend_m2: pdu.make_prop('blend_m2', LOWER_RENDERMODECD_ITEMS, pdu.make_id(LOWER_RENDERMODECD_BLENDCOLOR[0][0]))
    blend_a2: pdu.make_prop('blend_a2', LOWER_RENDERMODECD_ITEMS, pdu.make_id(LOWER_RENDERMODECD_BLENDALPHA[0][0]))
    blend_p2: pdu.make_prop('blend_p2', LOWER_RENDERMODECD_ITEMS, pdu.make_id(LOWER_RENDERMODECD_BLENDCOLOR[0][0]))

    num_cycles: IntProperty(name='num_cycles', default=1)


def mat_othermodeL_set(mat_othermodeL, cmd):
    mode = (cmd & 0xff0000000000) >> 40
    modename = next(filter(lambda e: e[2] == mode, LOWER_MODES))[0]

    mat_othermodeL.mode = pdu.make_id(modename)

    if mode in [MODE_ALPHACMP, MODE_ZSRC]:
        modebits = (cmd & 0xffffffff) >> mode
        items = LOWER_ALPHACOMP if mode == MODE_ALPHACMP else LOWER_ZSOURCE
        propval = next(filter(lambda e: e[2] == modebits, items))[0]
        propname = 'g_mdsft_alpha_compare' if mode == MODE_ALPHACMP else 'g_mdsft_zsrcsel'
        setattr(mat_othermodeL, propname, pdu.make_id(propval))
    else: # RENDERMODE
        mat_othermodeL.set_rendermode = True
        # cycle independent params
        modebits = (cmd & 0xfff8) >> 3
        for flag, (_, bits) in LOWER_RENDERMODECI_FLAGS.items():
            setattr(mat_othermodeL, flag, bool(modebits & bits))

        cvg_dst = (modebits & 0x60) >> 5
        propname = 'cvg_dst'
        propid = next(filter(lambda e: e[2] == cvg_dst, LOWER_RENDERMODECI_CVGDST))[0]
        setattr(mat_othermodeL, propname, pdu.make_id(propid))

        zmode = (modebits & 0x180) >> 7
        propname = 'zmode'
        propval = next(filter(lambda e: e[2] == zmode, LOWER_RENDERMODECI_ZMODE))[0]
        setattr(mat_othermodeL, propname, pdu.make_id(propval))

        # cycle dependent params
        blendparams = (cmd & 0xffff0000) >> 16

        # returns the nibble (set of 4 bits) at idx
        _nib = lambda idx: (blendparams & (0xf << (4*idx))) >> (4*idx)

        # upper and lower 2 bits in a nibble
        _upp = lambda w: (w & 0xC) >> 2
        _low = lambda w: (w & 0x3)

        b, m, a, p = _nib(0), _nib(1), _nib(2), _nib(3)

        b1, b2 = _upp(b), _low(b)
        m1, m2 = _upp(m), _low(m)
        a1, a2 = _upp(a), _low(a)
        p1, p2 = _upp(p), _low(p)

        names = [f'blend_{p}{n}' for p in ['b','m','a','p'] for n in [1,2]]
        values = [b1, b2, m1, m2, a1, a2, p1, p2]
        allitems = [
            LOWER_RENDERMODECD_BLENDMIX,
            LOWER_RENDERMODECD_BLENDCOLOR,
            LOWER_RENDERMODECD_BLENDALPHA,
            LOWER_RENDERMODECD_BLENDCOLOR,
        ]
        for i, (name, val) in enumerate(zip(names, values)):
            items = allitems[i//2]
            propid = next(filter(lambda e: e[2] == val, items))[0]
            setattr(mat_othermodeL, name, pdu.make_id(propid))

def enum_val(item, enum, idx):
    for e in enum:
        if e[0] == item:
            return e[idx]
    return -1

def mat_othermodeL_draw(othermodeL, layout, context):
    col: UILayout = layout.column(align=True)
    prop_split(col, othermodeL, "g_mdsft_alpha_compare", "Alpha Compare")
    prop_split(col, othermodeL, "g_mdsft_zsrcsel", "Z Source Selection")

    draw_rendermode(col, othermodeL)

def draw_rendermode(col, othermodeL):
    prop_split(col, othermodeL, 'aa_en'         ,'Antialiasing'),
    prop_split(col, othermodeL, 'z_cmp'         ,'Z Testing'),
    prop_split(col, othermodeL, 'z_upd'         ,'Z Writing'),
    prop_split(col, othermodeL, 'im_rd'         ,'IM_RD (?)'),
    prop_split(col, othermodeL, 'clr_on_cvg'    ,'Color on Coverage'),
    prop_split(col, othermodeL, 'cvg_dst'       ,'Coverage Destination'),
    prop_split(col, othermodeL, 'zmode'         ,'Z Mode'),
    prop_split(col, othermodeL, 'cvg_x_alpha'   ,'Coverage x Alpha'),
    prop_split(col, othermodeL, 'alpha_cvg_sel' ,'Coverage <> alpha'),
    prop_split(col, othermodeL, 'force_bl'      ,'Force Blending'),

    pdu.ui_separator(col, type='AUTO')

    header = 'Blender (Color = (P * A + M * B) / (A + B)'
    draw_blender(othermodeL, 1, header, col)

    if othermodeL.num_cycles == 2:
        pdu.ui_separator(col, type='AUTO')
        draw_blender(othermodeL, 2, 'Cycle 2', col)

def draw_blender(othermodeL, cycle, header, layout):
    ui_box = layout.box()
    ui_box.label(text=header)
    ui_blender = ui_box.row()
    col1 = ui_blender.column()
    col2 = ui_blender.column()
    col1.prop(othermodeL, f'blend_p{cycle}', text='P')
    col1.prop(othermodeL, f'blend_m{cycle}', text='M')
    col2.prop(othermodeL, f'blend_a{cycle}', text='A')
    col2.prop(othermodeL, f'blend_b{cycle}', text='B')

def othermodeL_rendermode_cmd(othermodeL):
    if not othermodeL: return 0

    # cycle independent params
    cvg_dst = pdu.enum_value(othermodeL, 'cvg_dst')
    zmode = pdu.enum_value(othermodeL, 'zmode')

    modebits = 0
    for flag, (_, bits) in LOWER_RENDERMODECI_FLAGS.items():
        modebits |= bits if getattr(othermodeL, flag) else 0

    modebits |= cvg_dst << 5
    modebits |= zmode << 7
    modebits <<= 3

    # cycle dependent params
    f = lambda e: pdu.enum_value(othermodeL, e)
    p1, a1, m1, b1 = f('blend_p1'), f('blend_a1'), f('blend_m1'), f('blend_b1')
    p2, a2, m2, b2 = f('blend_p2'), f('blend_a2'), f('blend_m2'), f('blend_b2')

    b = (b1 << 2) | (b2 << 0)
    m = (m1 << 6) | (m2 << 4)
    a = (a1 << 2) | (a2 << 0)
    p = (p1 << 6) | (p2 << 4)

    pa = (p | a)
    mb = (m | b)

    modebits |= ((pa << 8) | mb) << 16

    n = 29

    return (0xB900 << 8 * 6) | (MODE_RENDERMODE << 8 * 5) | (n << 8 * 4) | modebits
