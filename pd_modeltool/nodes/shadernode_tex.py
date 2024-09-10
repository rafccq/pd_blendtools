from .shadernode_base import PD_ShaderNodeBase

class PD_ShaderNodeTexConfig(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.textureconfig'
    bl_label = "TextureConfig"
    bl_icon = 'TEXTURE'

    def init(self, context):
        self.pd_init()

class PD_ShaderNodeTexLoad(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.textureload'
    bl_label = "TextureLoad"
    bl_icon = 'TEXTURE'

    def init(self, context):
        self.pd_init()

