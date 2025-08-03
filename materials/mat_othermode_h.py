from bpy.types import UILayout, PropertyGroup
from bpy.props import EnumProperty

from utils import pd_utils as pdu

from fast64.utility import prop_split
from fast64.f3d import f3d_enums


DESC_ALPHADITHER = f3d_enums.DESC_ALPHADITHER
DESC_RGBDITHER   = f3d_enums.DESC_RGBDITHER
DESC_CHROMAKEY   = f3d_enums.DESC_CHROMAKEY
DESC_TEXCONV     = f3d_enums.DESC_TEXCONV
DESC_TEXFILTER   = f3d_enums.DESC_TEXFILTER
DESC_TEXLUT      = f3d_enums.DESC_TEXLUT
DESC_TEXLOD      = f3d_enums.DESC_TEXLOD
DESC_TEXDETAIL   = f3d_enums.DESC_TEXDETAIL
DESC_TEXPERSP    = f3d_enums.DESC_TEXPERSP
DESC_CYCLETYPE   = f3d_enums.DESC_CYCLETYPE
DESC_PIPELINE    = f3d_enums.DESC_PIPELINE

ENUM_ALPHADITHER = f3d_enums.enumAlphaDither
ENUM_RGBDITHER = f3d_enums.enumRGBDither
ENUM_CHROMAKEY   = f3d_enums.enumCombKey
ENUM_TEXCONV     = f3d_enums.enumTextConv
ENUM_TEXFILTER   = f3d_enums.enumTextFilt
ENUM_TEXLUT      = f3d_enums.enumTextLUT
ENUM_TEXLOD      = f3d_enums.enumTextLOD
ENUM_TEXDETAIL   = f3d_enums.enumTextDetail
ENUM_TEXPERSP    = f3d_enums.enumTextPersp
ENUM_CYCLETYPE   = f3d_enums.enumCycleType
ENUM_PIPELINE    = f3d_enums.enumPipelineMode

NOT_SET = f3d_enums.NOT_SET


ENUM_UPPER_MODES = [
    ('g_mdsft_alpha_dither',  'Alpha Dither',              0x4),
    ('g_mdsft_rgb_dither',    'RGB Dither',                0x6),
    ('g_mdsft_combkey',       'Chroma Key',                0x8),
    ('g_mdsft_textconv',      'Texture Convert',           0x9),
    ('g_mdsft_text_filt',     'Texture Filter',            0x0c),
    ('g_mdsft_textlut',       'Texture LUT',               0x0e),
    ('g_mdsft_textlod',       'Texture LOD',               0x10),
    ('g_mdsft_textdetail',    'Texture Detail',            0x11),
    ('g_mdsft_textpersp',     'Texture Persp. Correction', 0x13),
    ('g_mdsft_cycletype',     'Cycle Type',                0x14),
    ('g_mdsft_pipeline',  'Pipeline Mode',             0x17),
]

UPPER_ITEMS = {
    'mode':                  ENUM_UPPER_MODES,
    'g_mdsft_alpha_dither':  ENUM_ALPHADITHER,
    'g_mdsft_rgb_dither':    ENUM_RGBDITHER,
    'g_mdsft_combkey':       ENUM_CHROMAKEY,
    'g_mdsft_textconv':      ENUM_TEXCONV,
    'g_mdsft_text_filt':     ENUM_TEXFILTER,
    'g_mdsft_textlut':       ENUM_TEXLUT,
    'g_mdsft_textlod':       ENUM_TEXLOD,
    'g_mdsft_textdetail':    ENUM_TEXDETAIL,
    'g_mdsft_textpersp':     ENUM_TEXPERSP,
    'g_mdsft_cycletype':     ENUM_CYCLETYPE,
    'g_mdsft_pipeline':  ENUM_PIPELINE,
}

UPPER_MODE_WIDTHS = {
    'g_mdsft_alpha_dither': 2,
    'g_mdsft_rgb_dither': 2,
    'g_mdsft_combkey': 1,
    'g_mdsft_textconv': 3,
    'g_mdsft_text_filt': 2,
    'g_mdsft_textlut': 2,
    'g_mdsft_textlod': 1,
    'g_mdsft_textdetail': 2,
    'g_mdsft_textpersp': 1,
    'g_mdsft_cycletype': 2,
    'g_mdsft_pipeline': 1,
}

UPPER_MODES = {
    0x4: ('g_mdsft_alpha_dither', f3d_enums.enumAlphaDither),
    0x6: ('g_mdsft_rgb_dither', f3d_enums.enumColorDither),
    0x8: ('g_mdsft_combkey', f3d_enums.enumCombKey),
    0x9: ('g_mdsft_textconv', f3d_enums.enumTextConv),
    0x0c: ('g_mdsft_text_filt', f3d_enums.enumTextFilt),
    0x0e: ('g_mdsft_textlut', f3d_enums.enumTextLUT),
    0x10: ('g_mdsft_textlod', f3d_enums.enumTextLOD),
    0x11: ('g_mdsft_textdetail', f3d_enums.enumTextDetail),
    0x13: ('g_mdsft_textpersp', f3d_enums.enumTextPersp),
    0x14: ('g_mdsft_cycletype', f3d_enums.enumCycleType),
    0x17: ('g_mdsft_pipeline', f3d_enums.enumPipelineMode),
}

TEXCONV = { 0b000: 0, 0b101: 1, 0b110: 2, }
TEXFILT = { 0b00: 0, 0b10: 1, 0b11: 2, }
TEXLUT = { 0b00: 0, 0b10: 1, 0b11: 2, }


class MatOtherModeH(PropertyGroup):
    g_mdsft_alpha_dither: EnumProperty( name="Alpha Dither", items=ENUM_ALPHADITHER, default=NOT_SET[0], description=DESC_ALPHADITHER)
    g_mdsft_rgb_dither: EnumProperty(name="RGB Dither", items=ENUM_RGBDITHER, default=NOT_SET[0], description=DESC_ALPHADITHER)
    g_mdsft_combkey: EnumProperty(name="Chroma Key", items=ENUM_CHROMAKEY, default=NOT_SET[0], description=DESC_ALPHADITHER)
    g_mdsft_textconv: EnumProperty(name="Texture Conv", items=ENUM_TEXCONV, default=NOT_SET[0], description=DESC_TEXCONV)
    g_mdsft_text_filt: EnumProperty(name="Texture Filter", items=ENUM_TEXFILTER, default=NOT_SET[0], description=DESC_TEXFILTER)
    g_mdsft_textlut: EnumProperty(name="Texture LUT", items=ENUM_TEXLUT, default=NOT_SET[0], description=DESC_TEXLUT)
    g_mdsft_textlod: EnumProperty(name="Texture LOD", items=ENUM_TEXLOD, default=NOT_SET[0], description=DESC_TEXLOD)
    g_mdsft_textdetail: EnumProperty(name="Texture Detail", items=ENUM_TEXDETAIL, default=NOT_SET[0], description=DESC_TEXDETAIL)
    g_mdsft_textpersp: EnumProperty(name="Texture Persp Corr", items=ENUM_TEXPERSP, default=NOT_SET[0], description=DESC_TEXPERSP)
    g_mdsft_cycletype: EnumProperty(name="Cycle Type", items=ENUM_CYCLETYPE, default=NOT_SET[0], description=DESC_CYCLETYPE)
    g_mdsft_pipeline: EnumProperty(name="Pipeline Mode", items=ENUM_PIPELINE, default=NOT_SET[0], description=DESC_PIPELINE)


def mat_othermodeH_set(mat_othermodeH, cmd):
    mode = (cmd & 0xff0000000000) >> 40
    mode_bits = (cmd & 0xffffffff) >> mode

    modes = UPPER_ITEMS['mode']
    modename = next(filter(lambda e: e[2] == mode, modes))[0]

    items = pdu.enum_items(mat_othermodeH, modename)
    item = pdu.enum_from_value(items, mode_bits)
    setattr(mat_othermodeH, modename, item.identifier)

def mat_othermodeH_draw(mat_othermodeH, layout, context):
    col: UILayout = layout.column(align=True)

    prop_split(col, mat_othermodeH, 'g_mdsft_alpha_dither',  'Alpha Dither')
    prop_split(col, mat_othermodeH, 'g_mdsft_rgb_dither',    'RGB Dither')
    prop_split(col, mat_othermodeH, 'g_mdsft_combkey',    'Chroma Key')
    prop_split(col, mat_othermodeH, 'g_mdsft_textconv',      'Texture Convert')
    prop_split(col, mat_othermodeH, 'g_mdsft_text_filt',    'Texture Filter')
    prop_split(col, mat_othermodeH, 'g_mdsft_textlut',       'Texture LUT')
    prop_split(col, mat_othermodeH, 'g_mdsft_textlod',       'Texture LOD')
    prop_split(col, mat_othermodeH, 'g_mdsft_textdetail',    'Texture Detail')
    prop_split(col, mat_othermodeH, 'g_mdsft_textpersp', 'Texture Persp. Correction')
    prop_split(col, mat_othermodeH, 'g_mdsft_cycletype',    'Cycle Type')
    prop_split(col, mat_othermodeH, 'g_mdsft_pipeline', 'Pipeline Mode')
