import bpy
from bpy.types import Panel, UIList

from utils import (
    pd_utils as pdu,
    setup_utils as stu,
)
from nodes import nodeutils as ndu
import pd_blendprops as pdprops


def draw_obj_base(layout, props_obj):
    row = layout.row().split(factor=0.7)
    row.prop(props_obj, 'extrascale', text='Scale')
    row.label(text=f'Hex {props_obj.extrascale:04X}')

    row = layout.row().split(factor=0.7)
    row.prop(props_obj, 'maxdamage', text='Health')
    row.label(text=f'Hex {props_obj.maxdamage:04X}')

    pdu.ui_separator(layout, type='LINE')

    pad = props_obj.pad
    hasbbox = pad.hasbbox
    row = layout.row().split(factor=0.04)
    row.prop(pad, 'hasbbox', text='')
    row.label(text='Bounds')
    if hasbbox:
        labels = [('xmin', 'xmax'), ('ymin', 'ymax'), ('zmin', 'zmax')]

        for idx in range(3):
            lmin = labels[idx][0]
            lmax = labels[idx][1]
            row = layout.row()
            row.prop(props_obj.pad, 'bbox', index=2 * idx, text=lmin)
            row.prop(props_obj.pad, 'bbox', index=2 * idx + 1, text=lmax)

    pdu.ui_separator(layout, type='LINE')
    flags1 = props_obj.flags1_packed
    flags2 = props_obj.flags2_packed
    flags3 = props_obj.flags3_packed
    layout.label(text=f'Flags: {flags1} | {flags2} | {flags3}')
    layout.operator('pdtools.setupobj_editflags', text=f'Edit Flags')
    layout.operator('pdtools.setupobj_editpadflags', text='Edit Pad')

    if stu.obj_hasmodel(props_obj):
        pdu.ui_separator(layout, type='LINE')
        box = layout.box()

        scn = bpy.context.scene
        modelnum = props_obj.modelnum
        modelname = scn.pd_modelfilenames[modelnum].name
        box.label(text=f'Model: {props_obj.modelname[:4]} ({modelname})')
        row = box.row().split(factor=0.9)

        row.prop(props_obj, 'modelname', text='')
        op = row.operator('pdtools.select_model', text='...')
        op.type = 'model'

def draw_door(props_door, layout, context, multiple):
    column = layout.column()

    pdu.ui_separator(column, type='LINE')
    row = column.row()
    row.prop(props_door, 'door_type', text='Type')
    sound = pdu.item_from_value(pdprops.DOOR_SOUNDTYPES, props_door.sound_type)
    row.popover(panel="PDTOOLS_PT_SetupDoorSound", text=f'Sound: {sound}')

    pdu.ui_separator(column, type='LINE')
    row = column.row().split(factor=0.45)
    flags = pdu.flags_pack(props_door.door_flags, [e[1] for e in pdprops.DOOR_FLAGS])
    row.popover(panel="PDTOOLS_PT_SetupDoorFlags", text=f'Door Flags: {flags:04X}')

    # a little hack: we set this attr to indicate to the panel we're using the 'key_flags' prop
    # all this because Blender won't allow us to pass any arbitrary data
    row = row.column()
    row.context_pointer_set(name='door_key_flags', data=None)
    flags = pdu.flags_pack(props_door.key_flags, [e[1] for e in pdprops.DOOR_KEYFLAGS])
    row.popover(panel="PDTOOLS_PT_SetupDoorFlags", text=f'Key Flags: {flags:08b}')

    pdu.ui_separator(column, type='LINE')
    col = layout.grid_flow(columns=2)
    col.prop(props_door, 'accel', text='Acceleration')
    col.prop(props_door, 'maxfrac', text='Dist Travels')
    col.prop(props_door, 'maxspeed', text='Max Speed')

    col.prop(props_door, 'decel', text='Deceleration')
    col.prop(props_door, 'perimfrac', text='Walkthru Dist')
    col.prop(props_door, 'autoclosetime', text='Time Open (ms)')
    col.prop(props_door, 'laserfade', text='Laser Opacity')

    row = layout.row()
    row.prop(props_door, 'sibling', text='Sibling')
    col = row.column()
    col.operator('pdtools.door_select_sibling', text='', icon='RESTRICT_SELECT_OFF')
    col.enabled = props_door.sibling is not None

def draw_lift(props_lift, layout, context, multiple):
    column = layout.column()

    pdu.ui_separator(column, type='LINE')
    column.label(text='Lift Doors')
    column.prop(props_lift, 'door1', text='Door 1')
    column.prop(props_lift, 'door2', text='Door 2')
    column.prop(props_lift, 'door3', text='Door 3')
    column.prop(props_lift, 'door4', text='Door 4')
    pdu.ui_separator(column, type='LINE')

    row = column.row().split(factor=0.6)
    row.prop(props_lift, 'accel', text='Min Speed')
    accel = int(0x10000 * props_lift.accel)
    row.label(text=f'hex: {pdu.s32(accel):08X}')

    row = column.row().split(factor=0.6)
    row.prop(props_lift, 'maxspeed', text='Max Speed')
    maxspeed = int(0x10000 * props_lift.maxspeed)
    row.label(text=f'hex: {pdu.s32(maxspeed):08X}')

    #### Lift Stops
    pdu.ui_separator(column, type='LINE')
    column.label(text='Lift Stops')
    stops = [props_lift.stop1, props_lift.stop2, props_lift.stop3, props_lift.stop4]
    for idx in range(4):
        row = column.row()
        row = row.split(factor=.2)
        row.label(text=f'Stop {idx + 1}:')
        if stops[idx]:
            row = row.split(factor=.9)
            row.label(text=f'{stops[idx].name}')
            op = row.operator('pdtools.op_setup_lift_remove_stop', icon='REMOVE', text='')
            op.index = idx
        else:
            op = row.operator('pdtools.op_setup_lift_create_stop', text='Create')
            op.index = idx

    pdu.ui_separator(column, type='LINE')
    column.label(text='Interlinks')

    row = layout.row()

    #### Interlinks
    interlinks = props_lift.interlinks
    row.template_list("PD_SETUPLIFT_UL_interlinks", "", props_lift, "interlinks", props_lift, "active_interlink_idx",
                      rows=4)

    col = row.column(align=True)
    col.operator("pdtools.op_setup_interlink_create", icon='ADD', text='')
    col_rem = col.column(align=True)
    col_rem.operator("pdtools.op_setup_interlink_remove", icon='REMOVE', text='')
    col_rem.enabled = len(interlinks) > 0

    if len(interlinks) > 0:
        row = layout.column()
        pdu.ui_separator(row, type='LINE')
        sel_interlink = interlinks[props_lift.active_interlink_idx]
        row.label(text=sel_interlink.name, icon='LINKED')
        row.prop(sel_interlink, 'controller', text='Controller')
        row = layout.column()
        row.prop(sel_interlink, 'controlled', text='Controlled')
        row.enabled = False
        row = layout.column()
        container = row.split(factor=.3)
        container.label(text='Lift Stop:')
        container.prop(sel_interlink, 'stopnum', text='')

def draw_tintedglass(props_glass, layout, context, multiple):
    pdu.ui_separator(layout, type='LINE')
    column = layout.row()
    column.prop(props_glass, 'opadist', text='Opa Dist')
    column.prop(props_glass, 'xludist', text='Xlu Dist')

def draw_weapon(props_weapon, layout, context, multiple):
    column = layout.column()
    pdu.ui_separator(column, type='LINE')
    column.prop(props_weapon, 'weaponnum', text='Weapon')


class PDTOOLS_PT_SetupObjectTools(Panel):
    bl_label = 'Object Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        scn = context.scene
        layout = self.layout

        box = layout.box()
        box.label(text='Create Object')
        box.prop(scn, 'pd_obj_type', text='Type')

        if not scn.pd_modelnames:
            box.label(text='No ROM Loaded', icon='ERROR')
            return

        obj_type = scn.pd_obj_type.lower()
        has_model = ['standard', 'door', 'glass', 'tinted glass', 'lift', 'multi-ammo crate']
        if obj_type in has_model:
            box2 = box.box()
            box2.label(text=f'Model: {scn.pd_model[:4]}')
            row = box2.row().split(factor=0.9)
            model = scn.pd_model
            item = scn.pd_modelnames[scn.pd_modelnames_idx]

            row.prop(scn, 'pd_model', text='')
            op = row.operator('pdtools.select_model', text='...')
            op.type = 'scene'

        if obj_type == 'weapon':
            pdu.ui_separator(box, type='LINE')
            row = box.row().split(factor=0.4)
            row.label(text='Weapon Pickup:')
            row.prop(scn, 'weapon_num', text='')

        ops = bpy.context.window.modal_operators if bpy.app.version >= (4, 2, 0) else []

        if 'PDTOOLS_OT_op_setup_object_create' in ops:
            box2 = box.box()
            box.alignment = 'CENTER'
            box.scale_x = 2.0
            box2.label(text='Click: create. Right click/ESC: end.', icon='INFO')
            context.workspace.status_text_set(text='Click on waypoints to add. Right click/ESC to end.')
        else:
            box.operator('pdtools.op_setup_object_create')
            context.workspace.status_text_set(None)


class PDTOOLS_PT_SetupDoorFlags(bpy.types.Panel):
    bl_label       = "Door Flags"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "HEADER"

    def draw(self, context):
        obj = context.active_object
        col = self.layout.column()
        usekeys = hasattr(context, 'door_key_flags')
        items = pdprops.DOOR_KEYFLAGS if usekeys else pdprops.DOOR_FLAGS
        propname = 'key_flags' if usekeys else 'door_flags'
        for idx, item in enumerate(items):
            col.prop(obj.pd_door, propname, index=idx, text=item[0], toggle=0)


class PDTOOLS_PT_SetupDoorSound(bpy.types.Panel):
    bl_label       = "Door Sound"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "HEADER"

    def draw(self, context):
        bl_obj = context.active_object
        props_door = bl_obj.pd_door

        row = self.layout.row()
        row.label(text='Door Sound')
        pdu.ui_separator(row, type='LINE')
        row = row.row()
        soundnum = props_door.sound_type[0:2].upper()
        # play sound: open
        op = row.operator('pdtools.door_play_sound', text='', icon='TRIA_RIGHT')
        op.open = True
        op.soundnum = soundnum

        # play sound: close
        row.context_pointer_set(name='doorclose', data=None)
        op = row.operator('pdtools.door_play_sound', text='', icon='RIGHTARROW')
        op.open = False
        op.soundnum = soundnum

        flow = self.layout.grid_flow(columns=2)
        flow.prop(props_door, 'sound_type', text='Sound', expand=1)


class PDTOOLS_PT_SetupObject(Panel):
    bl_label = 'Object'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and pdu.pdtype(obj) == pdprops.PD_OBJTYPE_PROP

    def draw(self, context):
        # if multiple selected, choose the first object selected (always the first to last in the list)
        multiple = len(context.selected_objects) > 1
        obj = context.selected_objects[-2] if multiple else context.active_object

        if not obj: return

        layout = self.layout
        column = layout.column()

        props_obj = obj.pd_prop
        txt = 'Multiple Selected' if multiple else f'{obj.name}'
        column.label(text=txt, icon='OBJECT_DATA')
        pdu.ui_separator(column, type='LINE')

        draw_obj_base(column, props_obj)

        self.bl_label = 'Object'
        if obj.pd_obj.type == pdprops.PD_PROP_DOOR:
            self.bl_label = 'Door'
            props_door = obj.pd_door
            draw_door(props_door, layout, context, multiple)
        elif obj.pd_obj.type == pdprops.PD_PROP_LIFT:
            self.bl_label = 'Lift'
            props_lift = obj.pd_lift
            draw_lift(props_lift, layout, context, multiple)
        elif obj.pd_obj.type == pdprops.PD_PROP_TINTEDGLASS:
            self.bl_label = 'Tinted Glass'
            props_glass = obj.pd_tintedglass
            draw_tintedglass(props_glass, layout, context, multiple)
        elif obj.pd_obj.type == pdprops.PD_PROP_WEAPON:
            self.bl_label = 'Weapon'
            props_weapon = obj.pd_weapon
            draw_weapon(props_weapon, layout, context, multiple)


class PDTOOLS_PT_SetupIntro(Panel):
    bl_label = 'Intro'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.pd_obj.type in [pdprops.PD_INTRO_CASE, pdprops.PD_INTRO_CASERESPAWN]

    def draw(self, context):
        # if multiple selected, choose the first object selected (always the first to last in the list)
        multiple = len(context.selected_objects) > 1
        obj = context.selected_objects[-2] if multiple else context.active_object

        if not obj: return

        layout = self.layout
        column = layout.column()

        props_obj = obj.pd_prop
        txt = 'Multiple Selected' if multiple else f'{obj.name}'
        column.label(text=txt, icon='OBJECT_DATA')
        pdu.ui_separator(column, type='LINE')

        column.operator('pdtools.setupobj_editpadflags', text=f'Edit Flags')

        if obj.pd_obj.type in [pdprops.PD_INTRO_CASE, pdprops.PD_INTRO_CASERESPAWN]:
            row = column.row()
            row.prop(obj.pd_intro, 'case_setnum', text='Set')


class PDTOOLS_PT_SetupWaypoint(Panel):
    bl_label = 'Waypoint'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return pdu.pdtype(obj) == pdprops.PD_OBJTYPE_WAYPOINT

    def draw(self, context):
        obj = context.object
        layout = self.layout

        props_waypoint = obj.pd_waypoint
        pd_neighbours_coll = props_waypoint.neighbours_coll
        index = props_waypoint.active_neighbour_idx

        layout.label(text=f'{obj.pd_obj.name}', icon='OBJECT_DATA')
        pdu.ui_separator(layout, type='LINE')

        row = layout.row().split(factor=0.3)
        row.label(text=f'ID: {props_waypoint.id:02X}')
        pdu.ui_separator(layout, type='LINE')
        row.prop(props_waypoint, 'group_enum', text='')

        row = layout.row()
        row.operator('pdtools.setupobj_editpadflags', text='Edit Pad')

        pdu.ui_separator(layout, type='LINE')

        box = layout.box()
        row = box.row()
        row.label(text=f'Neighbours ({len(props_waypoint.neighbours_coll)}):')
        row = box.row()
        row.template_list("PD_SETUPWAYPOINT_UL_neighbours", "", props_waypoint, "neighbours_coll", props_waypoint, "active_neighbour_idx", rows=4)
        col = row.column(align=True)
        col.operator('pdtools.op_setup_waypoint_addneighbour', icon='ADD', text='')
        col = col.column()
        col.operator('pdtools.op_setup_waypoint_removeneighbour', icon='REMOVE', text='')
        col.enabled = len(pd_neighbours_coll) > 0

        if len(pd_neighbours_coll) > 0:
            pd_neighbour = pd_neighbours_coll[index]
            row = box.row().split(factor=0.35)
            # row.label(text=f'{pd_neighbour.name} ({pd_neighbour.groupnum:02X})')
            row.label(text=f'{pd_neighbour.name}')
            row.prop(pd_neighbour, 'edgetype', text='')

        ops = bpy.context.window.modal_operators if bpy.app.version >= (4, 2, 0) else []

        if 'PDTOOLS_OT_op_setup_waypoint_addneighbour' in ops:
            box2 = box.box()
            box2.alignment = 'CENTER'
            box2.scale_x = 2.0
            box2.label(text='Click on waypoints to add', icon='INFO')
            box2.label(text='Right click/ESC to end')

        pdu.ui_separator(box, type='LINE')
        row = box.row()
        row.operator('pdtools.op_setup_waypoint_createneighbours', text='Create Neighbours')
        row = box.row()
        row.operator('pdtools.op_setup_waypoint_delete', text='Delete Waypoint')


class PDTOOLS_PT_WaypointTools(Panel):
    bl_label = 'Waypoints Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        sel_obj = context.active_object
        scn = context.scene
        layout = self.layout

        row = layout.row().split(factor=.35)
        row.label(text='Visibility:')
        row.prop(scn, 'pd_waypoint_vis', text='')

        pdu.ui_separator(layout, type='LINE')
        row = layout.row()
        op_props = row.operator('pdtools.op_setup_waypoint_create', text='Create Waypoint')

        row = layout.row()
        row.operator('pdtools.op_setup_waypoint_createfrommesh', text='Create From Mesh')
        row.enabled = sel_obj is not None


class PD_SETUPLIFT_UL_interlinks(UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname, _index):
        interlink = item

        layout.context_pointer_set("interlink", interlink)

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if interlink:
                layout.prop(interlink, 'name', text='', emboss=False, icon_value=icon)
            else:
                layout.label(text="", icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text='', icon_value=icon)


class PD_SETUPWAYPOINT_UL_neighbours(UIList):
    def draw_item(self, context, layout, _data, item, icon, _active_data, _active_propname, _index):
        bl_obj = context.active_object
        if not bl_obj: return

        waypoint = item

        pd_waypoint = bl_obj.pd_waypoint

        name = waypoint.name
        edgetype = waypoint.edgetype
        groupnum = waypoint.groupnum
        icon = 'ARROW_LEFTRIGHT'
        if edgetype == pdprops.WAYPOINT_EDGETYPES[1][0]:
            icon = 'FORWARD'
        elif edgetype == pdprops.WAYPOINT_EDGETYPES[2][0]:
            icon = 'TRACKING_FORWARDS_SINGLE'

        set_txt = '' if groupnum == pd_waypoint.groupnum else '*'
        text = f'{name} ({groupnum:02X}){set_txt}'
        layout.label(text=text, icon=icon)


classes = [
    PDTOOLS_PT_WaypointTools,
    PDTOOLS_PT_SetupObjectTools,
    PDTOOLS_PT_SetupObject,
    PDTOOLS_PT_SetupDoorFlags,
    PDTOOLS_PT_SetupDoorSound,
    PDTOOLS_PT_SetupWaypoint,
    PDTOOLS_PT_SetupIntro,
    PD_SETUPLIFT_UL_interlinks,
    PD_SETUPWAYPOINT_UL_neighbours,
]

register, unregister = bpy.utils.register_classes_factory(classes)
