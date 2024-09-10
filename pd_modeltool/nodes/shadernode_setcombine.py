from nodes.nodeutils import enum_name, make_prop
from .shadernode_base import PD_ShaderNodeBase

class PD_ShaderNodeSetCombine(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.setcombine'
    bl_label = "SetCombine"
    bl_icon = 'IMAGE_ZDEPTH'

    def init(self, context):
        self.pd_init()

