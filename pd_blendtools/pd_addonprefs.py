import bpy

import pd_utils as pdu

PD_PREF_ROMPATH = 'rompath'

PD_Prefs = [
    PD_PREF_ROMPATH
]

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

def _pref_value(prefs, key):
    if key == PD_PREF_ROMPATH:
        return prefs.rompath

def pref_get(key):
    if key not in PD_Prefs:
        raise RuntimeError(f'preference not found: {key}')

    name = pdu.addon_name()
    if name in bpy.context.preferences.addons:
        prefs = bpy.context.preferences.addons[name].preferences
        return _pref_value(prefs, key)

    blend_dir = bpy.path.abspath('//')
    configs = pdu.ini_file(f'{blend_dir}/config.ini')
    return configs[key]

def pref_save(key, value):
    if key not in PD_Prefs:
        raise RuntimeError(f'preference not found: {key}')

    name = pdu.addon_name()
    if name not in bpy.context.preferences.addons: return
    prefs = bpy.context.preferences.addons[name].preferences

    if key == PD_PREF_ROMPATH:
        prefs.rompath = value
