import bpy

import pd_utils as pdu

class PD_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = pdu.addon_name()

    rompath: bpy.props.StringProperty(
        name="Rom Path",
        description="Path to a valid Perfect Dark Rom",
        default='',
    )

    def draw(self, context):
        row = self.layout.row()

        row.prop(self, "rompath")
        row.operator("pdtools.load_rom")
