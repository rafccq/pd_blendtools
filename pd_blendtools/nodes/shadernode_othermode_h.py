from bpy.props import (
    EnumProperty
)

from nodes.nodeutils import make_prop, make_id
from .shadernode_base import PD_ShaderNodeBase


UPPER_MODES = [
    ('g_mdsft_alphadither',  'Alpha Dither',              0x4),
    ('g_mdsft_rgbdither',    'RGB Dither',                0x6),
    ('g_mdsft_chromakey',    'Chroma Key',                0x8),
    ('g_mdsft_texconv',      'Texture Convert',           0x9),
    ('g_mdsft_texfilter',    'Texture Filter',            0x0c),
    ('g_mdsft_texlut',       'Texture LUT',               0x0e),
    ('g_mdsft_texlod',       'Texture LOD',               0x10),
    ('g_mdsft_texdetail',    'Texture Detail',            0x11),
    ('g_mdsft_texperspcorr', 'Texture Persp. Correction', 0x13),
    ('g_mdsft_cycletype',    'Cycle Type',                0x14),
    ('g_mdsft_pipelinemode', 'Pipeline Mode',             0x17),
]

UPPER_ALPHADITHER = [
    ('Pattern', 'Pattern description',       0b00),
    ('No pattern', 'No pattern description', 0b01),
    ('Noise', 'Noise description',           0b10),
    ('Disable', 'Disable description',       0b11),
]

UPPER_RGBDITHER = [
    ('Magic Square', 'Magic Square Description', 0b00),
    ('Bayer',        'Bayer',   0b01),
    ('Noise',        'Noise',   0b10),
    ('Disable',      'Disable', 0b11),
]

UPPER_CHROMAKEY = [
    ('None', 'None Description', 0),
    ('Key', 'Key Description',   1),
]

UPPER_TEXCONV = [
    ('Convert', 'Convert description',                   0b000),
    ('Filter and Convert', 'Filter/Convert description', 0b101),
    ('Filter', 'Filter description',                     0b110),
]

UPPER_TEXFILTER = [
    ('Filter', 'Filter description',     0b00),
    ('Average', 'Average description',   0b10),
    ('Bilinear', 'Bilinear description', 0b11),
]

UPPER_TEXLUT = [
    ('None', 'None',     0b00),
    ('RGBA16', 'RGBA16', 0b10),
    ('IA16', 'IA16',     0b11),
]

UPPER_TEXLOD = [
    ('Tile', 'Tile description', 0),
    ('Lod', 'Lod description',   1),
]

UPPER_TEXDETAIL = [
    ('Clamp', 'Clamp description',     0b00),
    ('Sharpen', 'Sharpen description', 0b01),
    ('Detail', 'Detail description',   0b10),
]

UPPER_TEXPERSPCORR = [
    ('None', 'None description', 0),
    ('Perspective', 'Perspective description', 1),
]

UPPER_CYCLETYPE = [
    ('1 Cycle', '1 Cycle description', 0b00),
    ('2 Cycle', '2 Cycle description', 0b01),
    ('Copy', 'Copy description', 0b10),
    ('Fill', 'Fill description', 0b11),
]

UPPER_PIPELINEMODE = [
    ('1 Primitive', '1 Primitive description', 0),
    ('N Primitive', 'N Primitive description', 1),
]

UPPER_ITEMS = {
    'mode':                 UPPER_MODES,
    'g_mdsft_alphadither':  UPPER_ALPHADITHER,
    'g_mdsft_rgbdither':    UPPER_RGBDITHER,
    'g_mdsft_chromakey':    UPPER_CHROMAKEY,
    'g_mdsft_texconv':      UPPER_TEXCONV,
    'g_mdsft_texfilter':    UPPER_TEXFILTER,
    'g_mdsft_texlut':       UPPER_TEXLUT,
    'g_mdsft_texlod':       UPPER_TEXLOD,
    'g_mdsft_texdetail':    UPPER_TEXDETAIL,
    'g_mdsft_texperspcorr': UPPER_TEXPERSPCORR,
    'g_mdsft_cycletype':    UPPER_CYCLETYPE,
    'g_mdsft_pipelinemode': UPPER_PIPELINEMODE,
}

UPPER_MODE_WIDTHS = {
    'g_mdsft_alphadither': 2,
    'g_mdsft_rgbdither': 2,
    'g_mdsft_chromakey': 1,
    'g_mdsft_texconv': 3,
    'g_mdsft_texfilter': 2,
    'g_mdsft_texlut': 2,
    'g_mdsft_texlod': 1,
    'g_mdsft_texdetail': 2,
    'g_mdsft_texperspcorr': 1,
    'g_mdsft_cycletype': 2,
    'g_mdsft_pipelinemode': 1,
}


class PD_ShaderNodeSetOtherModeH(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.setothermodeH'
    bl_label = "SetOtherModeH"
    bl_icon = 'NODE_TEXTURE'

    min_width = 150

    def propagate_cycle_change(self, value):
        node = self
        while node:
            links = node.outputs[0].links
            if len(links) == 0: break

            node = links[0].to_node
            if node.bl_idname == 'pd.nodes.setothermodeH': break # TMP TODO add const

            node.set_num_cycles(value)

    def on_update(self, context):
        if not hasattr(context, 'enum'): return

        propname = context.enum.name
        propval = self.enum_value(propname)

        if propname == 'g_mdsft_cycletype':
            self.propagate_cycle_change(2 if propval == 1 else 1)

        mode = self.mode
        modeval = self.enum_value('mode')

        propname = mode if propname == 'mode' else propname
        n = UPPER_MODE_WIDTHS[propname]
        modes = UPPER_ITEMS['mode']
        ofs = next(filter(lambda e: e[0] == propname, modes))[2]
        mode_bits = propval << ofs

        self.cmd = f'BA00{modeval:02X}{n:02X}{mode_bits:08X}'

    mode: EnumProperty(
        name='mode', default='g_mdsft_alphadither',
        items = [(make_id(id), name, name, '', val) for (id, name, val) in UPPER_MODES], update=on_update,
    )

    g_mdsft_alphadither: make_prop('g_mdsft_alphadither', UPPER_ITEMS, 'pattern', on_update)
    g_mdsft_rgbdither: make_prop('g_mdsft_rgbdither', UPPER_ITEMS, 'magicsquare', on_update)
    g_mdsft_chromakey: make_prop('g_mdsft_chromakey', UPPER_ITEMS, 'none', on_update)
    g_mdsft_texconv: make_prop('g_mdsft_texconv', UPPER_ITEMS, 'filter', on_update)
    g_mdsft_texfilter: make_prop('g_mdsft_texfilter', UPPER_ITEMS, 'bilinear', on_update)
    g_mdsft_texlut: make_prop('g_mdsft_texlut', UPPER_ITEMS, 'none', on_update)
    g_mdsft_texlod: make_prop('g_mdsft_texlod', UPPER_ITEMS, 'tile', on_update)
    g_mdsft_texdetail: make_prop('g_mdsft_texdetail', UPPER_ITEMS, 'clamp', on_update)
    g_mdsft_texperspcorr: make_prop('g_mdsft_texperspcorr', UPPER_ITEMS, 'perspective', on_update)
    g_mdsft_cycletype: make_prop('g_mdsft_cycletype', UPPER_ITEMS, '1cycle', on_update)
    g_mdsft_pipelinemode: make_prop('g_mdsft_pipelinemode', UPPER_ITEMS, '1primitive', on_update)

    def init(self, context):
        self.pd_init()

    # def post_init(self):
    #     self.width = 280

    # updates the UI elements based on the command
    def update_ui(self):
        cmd = int(f'0x{self.cmd}', 16)
        mode = (cmd & 0xff0000000000) >> 40
        mode_bits = (cmd & 0xffffffff) >> mode

        modes = UPPER_ITEMS['mode']
        modename = next(filter(lambda e: e[2] == mode, modes))[0]

        self.mode = make_id(modename)

        items = UPPER_ITEMS[modename]
        modeval = next(filter(lambda e: e[2] == mode_bits, items))[0]
        setattr(self, modename, make_id(modeval))

    def draw_props(self, context, layout):
        super().draw_buttons(context, layout)

        col: UILayout = layout.column(align=True)
        col.label(text='Mode')
        col.context_pointer_set('enum', self.bl_rna.properties['mode'])
        col.prop(self, 'mode', text='')
        # col.separator(type='LINE')
        col.separator()

        mode = self.mode
        col.context_pointer_set('enum', self.bl_rna.properties[mode])
        col.prop(self, mode, text='')

    def draw_buttons(self, context, layout):
        self.draw_props(context, layout)

    def draw_buttons_ext(self, context, layout):
        self.draw_props(context, layout)


