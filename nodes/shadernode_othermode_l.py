from bpy.props import (
    BoolProperty, EnumProperty, IntProperty
)

from .nodeutils import make_prop, make_id
from .shadernode_base import PD_ShaderNodeBase
from utils import pd_utils as pdu

LOWER_ALPHACOMP = [
    ('None', 'None description',         0b00),
    ('Treshold', 'Treshold description', 0b01),
    ('Dither', 'Dither description',     0b11),
]

LOWER_ZSOURCE = [
    ('Pixel', 'Pixel description',         0),
    ('Primitive', 'Primitive description', 1),
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
    ('Alpha Compare',       'Alpha Compare',      MODE_ALPHACMP),
    ('Z Source Selection',  'Z Source Selection', MODE_ZSRC),
    ('Render Mode',         'Render Mode',        MODE_RENDERMODE),
]

DESC_LOWER_AA_EN         = 'AA_EN description'
DESC_LOWER_Z_CMP         = 'Z_CMP description'
DESC_LOWER_Z_UPD         = 'Z_UPD description'
DESC_LOWER_IM_RD         = 'IM_RD description'
DESC_LOWER_CLR_ON_CVG    = 'CLR_ON_CVG description'
DESC_LOWER_CVG_X_ALPHA   = 'CVG_X_ALPHA description'
DESC_LOWER_ALPHA_CVG_SEL = 'ALPHA_CVG_SEL description'
DESC_LOWER_FORCE_BL      = 'FORCE_BL description'

class PD_ShaderNodeSetOtherModeL(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.setothermodeL'
    bl_label = "SetOtherModeL"
    bl_icon = 'NODE_TEXTURE'

    min_width = 200

    def on_update(self, context):
        mode = self.enum_value('mode')

        if mode in [MODE_ALPHACMP, MODE_ZSRC]:
            if not hasattr(context, 'enum'):
                print(f'mode {mode} expected to have an enum pointer set')
                return

            ofs = 0 if mode == MODE_ALPHACMP else 2
            propname = 'g_mdsft_alphacompare' if mode == MODE_ALPHACMP else 'g_mdsft_zsrc'
            propval = self.enum_value(propname)

            modebits = propval << ofs
            n = 2 if mode == MODE_ALPHACMP else 1
        else:
            # cycle independent params
            cvg_dst = self.enum_value('cvg_dst')
            zmode = self.enum_value('zmode')

            modebits = 0
            for flag, (_, bits) in LOWER_RENDERMODECI_FLAGS.items():
                modebits |= bits if self.get(flag) else 0

            modebits |= cvg_dst << 5
            modebits |= zmode << 7
            modebits <<= 3

            # cycle dependent params
            f = self.enum_value
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

        self.cmd = f'B900{mode:02X}{n:02X}{modebits:08X}'

    hide: BoolProperty(name='Hide fields', default=False, description='Hide fields (still accessible in the panel)')

    mode: EnumProperty(
        name='mode', default='alphacompare',
        # items = [(make_id('mode', id), name, name) for (id, name, _) in LOWER_MODES], update=on_update,
        items = [(make_id(id), name, '', '', value) for (id, name, value) in LOWER_MODES], update=on_update,
    )

    g_mdsft_alphacompare: make_prop('g_mdsft_alphacompare', {'g_mdsft_alphacompare': LOWER_ALPHACOMP}, 'none', on_update)
    g_mdsft_zsrc: make_prop('g_mdsft_zsrc', {'g_mdsft_zsrc': LOWER_ZSOURCE}, 'pixel', on_update)

    aa_en: BoolProperty(name='aa_en', update=on_update, default=False, description=DESC_LOWER_AA_EN)
    z_cmp: BoolProperty(name='z_cmp', update=on_update, default=False, description=DESC_LOWER_Z_CMP)
    z_upd: BoolProperty(name='z_upd', update=on_update, default=False, description=DESC_LOWER_Z_UPD)
    im_rd: BoolProperty(name='im_rd', update=on_update, default=False, description=DESC_LOWER_IM_RD)
    clr_on_cvg: BoolProperty(name='clr_on_cvg', update=on_update, default=False, description=DESC_LOWER_CLR_ON_CVG)
    cvg_x_alpha: BoolProperty(name='cvg_x_alpha', update=on_update, default=False, description=DESC_LOWER_CVG_X_ALPHA)
    alpha_cvg_sel: BoolProperty(name='alpha_cvg_sel', update=on_update, default=False, description=DESC_LOWER_ALPHA_CVG_SEL)
    force_bl: BoolProperty(name='force_bl', update=on_update, default=False, description=DESC_LOWER_FORCE_BL)

    # cycle independent props
    cvg_dst: make_prop('cvg_dst', {'cvg_dst': LOWER_RENDERMODECI_CVGDST}, 'clamp', on_update)
    zmode: make_prop('zmode', {'zmode': LOWER_RENDERMODECI_ZMODE}, 'opaque', on_update)

    # cycle dependent props cycle 1
    blend_b1: make_prop('blend_b1', LOWER_RENDERMODECD_ITEMS, make_id(LOWER_RENDERMODECD_BLENDMIX[0][0]), on_update)
    blend_m1: make_prop('blend_m1', LOWER_RENDERMODECD_ITEMS, make_id(LOWER_RENDERMODECD_BLENDCOLOR[0][0]), on_update)
    blend_a1: make_prop('blend_a1', LOWER_RENDERMODECD_ITEMS, make_id(LOWER_RENDERMODECD_BLENDALPHA[0][0]), on_update)
    blend_p1: make_prop('blend_p1', LOWER_RENDERMODECD_ITEMS, make_id(LOWER_RENDERMODECD_BLENDCOLOR[0][0]), on_update)

    # cycle dependent props cycle 2
    blend_b2: make_prop('blend_b2', LOWER_RENDERMODECD_ITEMS, make_id(LOWER_RENDERMODECD_BLENDMIX[0][0]), on_update)
    blend_m2: make_prop('blend_m2', LOWER_RENDERMODECD_ITEMS, make_id(LOWER_RENDERMODECD_BLENDCOLOR[0][0]), on_update)
    blend_a2: make_prop('blend_a2', LOWER_RENDERMODECD_ITEMS, make_id(LOWER_RENDERMODECD_BLENDALPHA[0][0]), on_update)
    blend_p2: make_prop('blend_p2', LOWER_RENDERMODECD_ITEMS, make_id(LOWER_RENDERMODECD_BLENDCOLOR[0][0]), on_update)

    num_cycles: IntProperty(name='num_cycles', default=1)

    def init(self, context):
        self.pd_init()

    def post_init(self):
        self.init_num_cycles()

    def update_ui(self):
        cmd = int(f'0x{self.cmd}', 16)
        mode = (cmd & 0xff0000000000) >> 40

        modename = next(filter(lambda e: e[2] == mode, LOWER_MODES))[0]

        self.mode = make_id(modename)

        if mode in [MODE_ALPHACMP, MODE_ZSRC]:
            modebits = (cmd & 0xffffffff) >> mode
            items = LOWER_ALPHACOMP if mode == MODE_ALPHACMP else LOWER_ZSOURCE
            propval = next(filter(lambda e: e[2] == modebits, items))[0]
            propname = 'g_mdsft_alphacompare' if mode == MODE_ALPHACMP else 'g_mdsft_zsrc'
            setattr(self, propname, make_id(propval))
        else: # RENDERMODE
            # cycle independent params
            modebits = (cmd & 0xfff8) >> 3
            for flag, (_, bits) in LOWER_RENDERMODECI_FLAGS.items():
                setattr(self, flag, bool(modebits & bits))

            cvg_dst = (modebits & 0x60) >> 5
            propname = 'cvg_dst'
            propid = next(filter(lambda e: e[2] == cvg_dst, LOWER_RENDERMODECI_CVGDST))[0]
            setattr(self, propname, make_id(propid))

            zmode = (modebits & 0x180) >> 7
            propname = 'zmode'
            propval = next(filter(lambda e: e[2] == zmode, LOWER_RENDERMODECI_ZMODE))[0]
            setattr(self, propname, make_id(propval))

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
                setattr(self, name, make_id(propid))

    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)

        col: UILayout = layout.column(align=True)
        col.prop(self, 'hide')
        if not self.hide:
            pdu.ui_separator(col, type='LINE')
            self.draw_props(context, col, col_layout=True)

    def draw_buttons_ext(self, context, layout):
        self.draw_props(context, layout, False, True)

    def draw_props(self, _context, layout, col_layout, blender_textfull=False):
        col: UILayout = layout.column(align=True)
        col.label(text='Mode')
        col.context_pointer_set('enum', self.bl_rna.properties['mode'])
        col.prop(self, 'mode', text='')
        # col.label(text='Options')
        pdu.ui_separator(col, type='LINE')

        mode = self.enum_value('mode')

        if mode == MODE_ALPHACMP:
            col.context_pointer_set('enum', self.bl_rna.properties['g_mdsft_alphacompare'])
            col.prop(self, 'g_mdsft_alphacompare', text='')
        elif mode == MODE_ZSRC:
            # col.label(text='Z Source Sel')
            col.context_pointer_set('enum', self.bl_rna.properties['g_mdsft_zsrc'])
            col.prop(self, 'g_mdsft_zsrc', text='')
        elif mode == MODE_RENDERMODE:
            for name, (label, _) in LOWER_RENDERMODECI_FLAGS.items():
                col.prop(self, name, text=label)

            col.label(text='Coverage Destination')
            col.context_pointer_set('enum', self.bl_rna.properties['cvg_dst'])
            col.prop(self, 'cvg_dst', text='')

            pdu.ui_separator(col, type='AUTO')

            col.label(text='Z Mode')
            col.context_pointer_set('enum', self.bl_rna.properties['zmode'])
            col.prop(self, 'zmode', text='')

            pdu.ui_separator(col, type='AUTO')

            header = 'Blender (Color = (P * A + M * B) / (A + B)' if blender_textfull else 'Cycle 1'
            self.draw_blender(1, header, col, col_layout)

            if self.num_cycles == 2:
                pdu.ui_separator(col, type='AUTO')
                self.draw_blender(2, 'Cycle 2', col, col_layout)

    def draw_blender(self, cycle, header, layout, col_layout):
        if col_layout:
            box = layout.box()
            box.label(text=f'Cycle {cycle}')
            col = box.column()
            # col.label(text='P')
            col.prop(self, f'blend_p{cycle}', text='P')
            col.prop(self, f'blend_m{cycle}', text='M')
            col.prop(self, f'blend_a{cycle}', text='A')
            col.prop(self, f'blend_b{cycle}', text='B')
        else:
            ui_box = layout.box()
            ui_box.label(text=header)
            ui_blender = ui_box.row()
            col1 = ui_blender.column()
            col2 = ui_blender.column()
            col1.prop(self, f'blend_p{cycle}', text='P')
            col1.prop(self, f'blend_m{cycle}', text='M')
            col2.prop(self, f'blend_a{cycle}', text='A')
            col2.prop(self, f'blend_b{cycle}', text='B')

    def set_num_cycles(self, num_cycles):
        self.num_cycles = num_cycles

