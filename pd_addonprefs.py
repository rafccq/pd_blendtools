import bpy
from pd_blendtools import addon_updater_ops

from utils import pd_utils as pdu

@addon_updater_ops.make_annotations
class PD_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    rompath: bpy.props.StringProperty(
        name="Rom Path",
        description="Path to a valid Perfect Dark Rom",
        default='',
    )

    # ######### ADDON UPDATER #########
    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)

    updater_interval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)

    updater_interval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31)

    updater_interval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)

    updater_interval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)
    # ####################################

    def draw(self, context):
        row = self.layout.row()

        addon_updater_ops.check_for_update_background()

        row.prop(self, "rompath")
        row.operator("pdtools.load_rom")
        addon_updater_ops.update_settings_ui(self, context)
        addon_updater_ops.update_notice_box_ui(self, context)

def addon_prefs():
    addon = bpy.context.preferences.addons.get(__package__, None)
    if not addon:
        print(f'ERROR: addon not found: {__package__}')
        return None

    return addon.preferences

def rompath():
    prefs = addon_prefs()
    if not prefs: return

    return prefs.rompath

def set_rompath(rompath):
    prefs = addon_prefs()
    if not prefs: return

    prefs.rompath = rompath
