from nodes.nodeutils import enum_name, make_prop
from .shadernode_base import PD_ShaderNodeBase

LOWER_ALPHACOMP = [
    ('None', 'None description',         0b00),
    ('Treshold', 'Treshold description', 0b01),
    ('Dither', 'Dither description',     0b11),
]

LOWER_ZSOURCE = [
    ('Pixel', 'Pixel description',         0),
    ('Primitive', 'Primitive description', 1),
]

LOWER_RENDERMODECI_FLAGS = [
    ('AA_EN', 'Antialiasing',              1),
    ('Z_CMP', 'Z Testing',                 1 << 1),
    ('Z_UPD', 'Z Writing',                 1 << 2),
    ('IM_RD', 'IM_RD (?)',                 1 << 3),
    ('CLR_ON_CVG', 'Color on Coverage',    1 << 4),
    ('CVG_X_ALPHA', 'Coverage x Alpha',    1 << 9),
    ('ALPHA_CVG_SEL', 'Coverage <> alpha', 1 << 10),
    ('FORCE_BL', 'Force Blending',         1 << 11),
]

class PD_ShaderNodeSetOtherModeL(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.setothermodeL'
    bl_label = "SetOtherModeL"
    bl_icon = 'NODE_TEXTURE'

    def init(self, context):
        self.pd_init()
