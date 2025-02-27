import bpy
from bpy.types import PropertyGroup, Panel, UIList, UI_UL_list, Scene, Context
from bpy.props import IntProperty, StringProperty, BoolProperty, CollectionProperty, BoolVectorProperty

from pd_blendprops import TILE_FLAGS
from model_import import MeshLayer
import pd_addonprefs as pdp
import pd_blendprops as pdprops
import pd_utils as pdu
import pd_ops as pdo
import nodes.nodeutils as ndu


class PDTOOLS_PT_PanelModel(Panel):
    bl_label = "Model"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PD Tools"

    def draw(self, context: Context) -> None:
        self.layout.operator_context = "INVOKE_DEFAULT"
        row = self.layout.row()

        rompath = pdp.pref_get(pdp.PD_PREF_ROMPATH)
        rom_exists = bool(rompath)

        row.enabled = rom_exists
        icon = 'NONE' if rompath else 'ERROR'
        row.operator("pdtools.import_model_rom", icon=icon)

        row = self.layout.row()
        row.operator("pdtools.import_model_file")
        row.enabled = rom_exists

        obj = context.object
        row = self.layout.row()
        # ismodel = pdu.pdtype(obj) == pdprops.PD_OBJTYPE_MODEL
        ismodel = obj is not None and (obj.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_MODEL
        # print(ismodel, obj.pd_obj.type if obj is not None else '-')
        row.enabled = rom_exists and ismodel
        row.operator("pdtools.export_model", text = "Export Model")


class PDTOOLS_PT_ModelProps(Panel):
    bl_label = 'PD Model'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and (obj.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_MODEL

    def draw(self, context):
        layout = self.layout
        props = context.object.pd_model

        box = layout.box()
        box.prop(props, 'name', icon='LOCKED', text='')

        if props.idx >= 0:
            box.label(text=f'Index: {props.idx:02X}', icon='LOCKED')

        if props.layer >= 0:
            txtlayer = 'opa' if props.layer == MeshLayer.OPA else 'xlu'
            box.label(text=f'Layer: {txtlayer}', icon='LOCKED')
        box.enabled = False

class PDTOOLS_PT_Room(Panel):
    bl_label = 'Room'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"
    # bl_context = "object"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return pdu.pdtype(obj) in [pdprops.PD_OBJTYPE_ROOM, pdprops.PD_OBJTYPE_ROOMBLOCK]

    def draw(self, context):
        bl_obj = context.object
        scn = context.scene
        layout = self.layout

        isroom = pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOM

        pd_room = bl_obj.pd_room

        box = layout.box()
        name = 'Room' if isroom else 'Block'
        num = pd_room.roomnum if isroom else pd_room.blocknum

        if isroom:
            box.label(text=f'{name} {num:02X}', icon='OBJECT_DATA')
            row = box.row()
            row.operator('pdtools.op_room_create_block', text=f'Create Block')
        else:
            row = box.row()
            row.alignment = 'LEFT'
            row.emboss = 'NONE'
            row.label(text='', icon='OBJECT_DATA')
            row.operator('pdtools.op_room_select_room', text=f'Room {pd_room.roomnum:02X}')
            row.label(text='', icon='RIGHTARROW')
            row.label(text=f'{name} {num}')

            box.label(text=f'Type: {pd_room.blocktype}', icon='LOCKED')
            row = box.row()
            row.prop(pd_room, 'layer', text='Layer')
            row.enabled = False
            box.prop(pd_room, 'parent_enum', text='Parent')

            if pd_room.blocktype == pdprops.BLOCKTYPE_BSP:
                box.separator(type='LINE')
                box.label(text='BSP Position:')
                box.prop(pd_room, 'bsp_pos', text='')
                # col = box.row()
                # for idx, t in enumerate(['X', 'Y', 'Z']):
                #     col.prop(pd_room, 'bsp_pos', index = idx, text=t)

                box.label(text='BSP Normal:')
                box.prop(pd_room, 'bsp_normal', text='')
                row = box.row()
                for idx, t in enumerate(['X', 'Y', 'Z']):
                    row.prop(pd_room, 'bsp_normal', index = idx, text=t)
                # box.prop(pd_room, 'bsp_normal', text='BSP Normal')
                row = box.row()
                row.prop(scn, 'pd_bspwidth', text='Width (View Only)')
                box.separator(type='LINE')
                box.operator('pdtools.op_room_create_block', text=f'Create Block')


class PDTOOLS_PT_Portal(Panel):
    bl_label = 'PD Portal'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return pdu.pdtype(obj) == pdprops.PD_OBJTYPE_PORTAL

    def draw(self, context):
        obj = context.object
        layout = self.layout

        props_portal = obj.pd_portal

        box = layout.box()
        box.label(text=f'{obj.pd_obj.name}', icon='OBJECT_DATA')
        box.prop(props_portal, 'room1', text='room 1')
        box.prop(props_portal, 'room2', text='room 2')
        box.operator("pdtools.portal_find_rooms", text = "Auto Find")


def draw_row(props, label, name, layout, factor):
    container = layout.split(factor=factor)
    container.label(text=label)
    container.prop(props, name, text='')

class PDTOOLS_PT_Tile(Panel):
    bl_label = 'Tile'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and (obj.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_TILE

    def draw(self, context):
        # if multiple selected, choose the first object selected (always the first to last in the list)
        multiple = len(context.selected_objects) > 1
        obj = context.selected_objects[-2] if multiple else context.active_object

        if not obj: return

        layout = self.layout

        column = layout.column()

        props_tile = obj.pd_tile
        txt = 'Multiple Selected' if multiple else f'{obj.name}'
        column.label(text=txt, icon='OBJECT_DATA')
        column.separator(type='LINE')

        draw_row(props_tile, 'Room', 'room', column, .35)
        draw_row(props_tile, 'Floor Color', 'floorcol', column, .35)
        draw_row(props_tile, 'Floor Type', 'floortype', column, .35)

        box = column.box()
        box.label(text=f'Flags')
        container = box.grid_flow(columns=2, align=True)

        for idx, flag in enumerate(TILE_FLAGS):
            container.prop(props_tile, 'flags', index=idx, text=flag)

        if multiple:
            column.context_pointer_set(name='pd_tile', data=obj.pd_tile)
            column.operator("pdtools.tile_apply_props", text = "Apply To Selection")


class PDTOOLS_PT_TileTools(Panel):
    bl_label = 'Tile Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        box = layout.box()
        box.label(text='Highlight')
        box.prop(scn, 'pd_tile_hilightmode', text='Mode')

        if scn.pd_tile_hilightmode == 'flags':
            container = box.grid_flow(columns=2, align=True)
            for idx, flag in enumerate(TILE_FLAGS):
                container.prop(scn.pd_tile_hilight, 'flags', index=idx, text=flag, toggle=True)
        elif scn.pd_tile_hilightmode == 'room':
            container = box.row()
            container.prop(scn.pd_tile_hilight, 'room', text='Room')

        row = layout.row()
        row.operator('pdtools.op_tiles_select_room', text='Select All In The Same Room')

        bl_tile = context.active_object
        nsel = len(context.selected_objects)
        row.enabled = bool(bl_tile) and pdu.pdtype(bl_tile) == pdprops.PD_OBJTYPE_TILE and nsel == 1


class PDTOOLS_PT_RoomTools(Panel):
    bl_label = 'Room Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        scn = context.scene
        layout = self.layout

        col = layout.column()
        container = col.split(factor=.5)
        container.label(text=f'Go To Room')
        container.prop(scn, 'pd_room_goto', text='')

        sel = context.selected_objects
        nsel = len(sel)
        objtype = lambda ob, types: pdu.pdtype(ob) in types
        isroom = lambda o: pdu.pdtype(o) == pdprops.PD_OBJTYPE_ROOMBLOCK

        bl_obj = context.active_object
        pdtype = pdu.pdtype(bl_obj)

        row = col.row()
        row = row.split(factor=0.5)
        col = row.column()
        col.operator(pdo.PDTOOLS_OT_RoomSplitByPortal.bl_idname, text='Split By Portal')
        portalselected = context.scene.pd_portal is not None
        col.enabled = isroom(bl_obj) and portalselected
        row.prop(scn, 'pd_portal', text='')

        row = layout.column()
        row.operator(pdo.PDTOOLS_OT_RoomSelectAllBlocks.bl_idname, text='Select All Blocks In Room')
        row.enabled = nsel == 1 and pdtype in [pdprops.PD_OBJTYPE_ROOM, pdprops.PD_OBJTYPE_ROOMBLOCK]


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
        row.separator(type='LINE')
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


class PDTOOLS_PT_SetupDoor(Panel):
    bl_label = 'Door'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.pd_obj.type == pdprops.PD_PROP_DOOR

    def draw(self, context):
        # if multiple selected, choose the first object selected (always the first to last in the list)
        multiple = len(context.selected_objects) > 1
        obj = context.selected_objects[-2] if multiple else context.active_object

        if not obj: return

        layout = self.layout

        column = layout.column()

        props_obj = obj.pd_prop
        props_door = obj.pd_door
        txt = 'Multiple Selected' if multiple else f'{obj.name}'
        column.label(text=txt, icon='OBJECT_DATA')
        column.separator(type='LINE')

        column.label(text='Bounds')
        labels = [('xmin', 'xmax'), ('ymin', 'ymax'), ('zmin', 'zmax')]
        for idx in range(3):
            lmin = labels[idx][0]
            lmax = labels[idx][1]
            row = column.row()
            row.prop(props_obj.pad, 'bbox', index=2*idx,   text=lmin)
            row.prop(props_obj.pad, 'bbox', index=2*idx+1, text=lmax)

        column.separator(type='LINE')
        row = column.row()
        row.prop(props_door, 'door_type', text='Type')
        sound = ndu.item_from_value(pdprops.DOOR_SOUNDTYPES, props_door.sound_type)
        row.popover(panel="PDTOOLS_PT_SetupDoorSound", text=f'Sound: {sound}')

        column.separator(type='LINE')
        row = column.row().split(factor=0.45)
        flags = pdu.flags_pack(props_door.door_flags, [e[1] for e in pdprops.DOOR_FLAGS])
        row.popover(panel="PDTOOLS_PT_SetupDoorFlags", text=f'Door Flags: {flags:04X}')

        # a little hack: we set this attr to indicate to the panel we're using the 'key_flags' prop
        # all this because Blender won't allow us to pass any arbitrary data
        row = row.column()
        row.context_pointer_set(name='door_key_flags', data=None)
        flags = pdu.flags_pack(props_door.key_flags, [e[1] for e in pdprops.DOOR_KEYFLAGS])
        row.popover(panel="PDTOOLS_PT_SetupDoorFlags", text=f'Key Flags: {flags:08b}')

        column.separator(type='LINE')
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


class PDTOOLS_PT_SetupTintedGlass(Panel):
    bl_label = 'Tinted Glass'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.pd_obj.type == pdprops.PD_PROP_TINTED_GLASS

    def draw(self, context):
        # if multiple selected, choose the first object selected (always the first to last in the list)
        multiple = len(context.selected_objects) > 1
        obj = context.selected_objects[-2] if multiple else context.active_object

        if not obj: return

        layout = self.layout

        column = layout.column()

        props_prop = obj.pd_prop
        props_glass = obj.pd_tintedglass
        txt = 'Multiple Selected' if multiple else f'{obj.name}'
        column.label(text=txt, icon='OBJECT_DATA')
        column.separator(type='LINE')

        column.label(text='Bounds')
        labels = [('xmin', 'xmax'), ('ymin', 'ymax'), ('zmin', 'zmax')]
        for idx in range(3):
            lmin = labels[idx][0]
            lmax = labels[idx][1]
            row = column.row()
            row.prop(props_prop, 'pad_bbox', index=2*idx, text=lmin)
            row.prop(props_prop, 'pad_bbox', index=2*idx+1, text=lmax)

        column.separator(type='LINE')
        column.prop(props_glass, 'opadist', text='Opa Dist')


class PDTOOLS_PT_SetupWaypoint(Panel):
    bl_label = 'PD Waypoint'
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

        box = layout.box()
        box.label(text=f'{obj.pd_obj.name}', icon='OBJECT_DATA')
        row = box.row().split(factor=0.4)
        row.label(text=f'ID: {props_waypoint.id:02X}')
        box.separator(type='LINE')
        row.prop(props_waypoint, 'group_enum', text='')
        # box.prop(props_waypoint, 'neighbours', text='Neighbours')
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

        box.separator(type='LINE')
        row = box.row()
        # col = row.column()
        # col.operator('pdtools.op_setup_waypoint_addneighbour', text='Add Neighbours')
        # col = row.column()
        # col.operator('pdtools.op_setup_waypoint_removeneighbour', text='Remove Neighbour')
        # row = box.row()
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

        layout.separator(type='LINE')
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


class PDTOOLS_PT_SetupLift(Panel):
    bl_label = 'Lift'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.pd_obj.type == pdprops.PD_PROP_LIFT

    def draw(self, context):
        # if multiple selected, choose the first object selected (always the first to last in the list)
        multiple = len(context.selected_objects) > 1
        obj = context.selected_objects[-2] if multiple else context.active_object

        if not obj: return

        layout = self.layout

        column = layout.column()

        props_obj = obj.pd_prop
        props_lift = obj.pd_lift
        txt = 'Multiple Selected' if multiple else f'{obj.name}'
        column.label(text=txt, icon='OBJECT_DATA')
        column.separator(type='LINE')

        column.label(text='Bounds')
        labels = [('xmin', 'xmax'), ('ymin', 'ymax'), ('zmin', 'zmax')]
        for idx in range(3):
            lmin = labels[idx][0]
            lmax = labels[idx][1]
            row = column.row()
            row.prop(props_obj, 'pad_bbox', index=2*idx, text=lmin)
            row.prop(props_obj, 'pad_bbox', index=2*idx+1, text=lmax)

        column.separator(type='LINE')
        column.operator('pdtools.setupobj_editflags')

        column.separator(type='LINE')
        column.label(text='Lift Doors')
        column.prop(props_lift, 'door1', text='Door 1')
        column.prop(props_lift, 'door2', text='Door 2')
        column.prop(props_lift, 'door3', text='Door 3')
        column.prop(props_lift, 'door4', text='Door 4')
        column.separator(type='LINE')
        column.prop(props_lift, 'accel', text='Acceleration')
        column.prop(props_lift, 'maxspeed', text='Max Speed')

        #### Lift Stops
        column.separator(type='LINE')
        column.label(text='Lift Stops')
        stops = [props_lift.stop1, props_lift.stop2, props_lift.stop3, props_lift.stop4]
        for idx in range(4):
            row = column.row()
            row = row.split(factor=.2)
            row.label(text=f'Stop {idx + 1}:')
            if stops[idx]:
                row = row.split(factor=.9)
                row.label(text=f'{stops[idx].name}')
                op = row.operator(pdo.PDTOOLS_OT_SetupLiftRemoveStop.bl_idname, icon='REMOVE', text='')
                op.index = idx
            else:
                op = row.operator(pdo.PDTOOLS_OT_SetupLiftCreateStop.bl_idname, text='Create')
                op.index = idx

        column.separator(type='LINE')
        column.label(text='Interlinks')

        row = layout.row()

        #### Interlinks
        interlinks = props_lift.interlinks
        row.template_list("PD_SETUPLIFT_UL_interlinks", "", props_lift, "interlinks", props_lift, "active_interlink_idx", rows=4)

        col = row.column(align=True)
        col.operator("pdtools.op_setup_interlink_create", icon='ADD', text='')
        col_rem = col.column(align=True)
        col_rem.operator("pdtools.op_setup_interlink_remove", icon='REMOVE', text='')
        col_rem.enabled = len(interlinks) > 0

        if len(interlinks) > 0:
            row = layout.column()
            row.separator(type='LINE')
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


class PDTOOLS_PT_Scene(Panel):
    bl_label = 'Scene'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        togg = True

        layout = self.layout
        box = layout.box()
        box.label(text=f'Visibility')
        container = box.grid_flow(columns=3, align=True)
        for idx, name in enumerate(pdprops.PD_COLLECTIONS):
            container.prop(context.scene, 'collections_vis', index=idx, toggle=togg, text=name)

        box = layout.box()
        box.label(text=f'Selection')
        container = box.grid_flow(columns=3, align=True)
        for idx, name in enumerate(pdprops.PD_COLLECTIONS):
            container.prop(context.scene, 'collections_sel', index=idx, toggle=togg, text=name)


class PDModelListItem(PropertyGroup):
    filename: StringProperty(name='filename')
    alias: StringProperty(name='alias')


class PDTOOLS_UL_ModelList(UIList):
    #note: only in v4.2+ the filter will update as you type
    filter_name: StringProperty(name="filter_name", options={"TEXTEDIT_UPDATE"})
    filter_type: bpy.props.EnumProperty(
        items=[("Props", "Props", "Props", 'Props Models', 1),
               ("Guns", "Guns", "Guns", 'Guns Models', 2),
               ("Chars", "Chars", "Chars", 'Character Models', 3)],
        name="Model Type",
        description="Model Type",
        default="Guns",
    )

    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            text = item.filename
            if item.alias: text += f' ({item.alias})'
            layout.label(text=text, translate=False, icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

    def draw_filter(self, _context, layout):
        row = layout.row(align=True)
        row.prop(self, "filter_name", text="Filter", icon="VIEWZOOM")
        row = layout.row(align=True)
        row.prop(self, "filter_type", expand=True)

    def filter_items(self, _context, data, prop):
        items = getattr(data, prop)
        if not len(items):
            return [], []

        if self.filter_name:
            flt_flags = UI_UL_list.filter_items_by_name(
                self.filter_name,
                self.bitflag_filter_item,
                items,
                propname="filename")
        else:
            flt_flags = [self.bitflag_filter_item] * len(items)

        for idx, item in enumerate(items):
            name = item.filename
            f_type = flt_flags[idx] if name[0] == self.filter_type[0] else 0
            flt_flags[idx] &= f_type

        return flt_flags, []

classes = [
    PDTOOLS_PT_PanelModel,
    PDTOOLS_PT_Scene,
    PDTOOLS_PT_TileTools,
    PDTOOLS_PT_RoomTools,
    PDTOOLS_PT_WaypointTools,
    PDTOOLS_UL_ModelList,
    PDTOOLS_PT_Room,
    PDTOOLS_PT_Portal,
    PDTOOLS_PT_Tile,
    PDModelListItem,
    PDTOOLS_PT_SetupDoor,
    PDTOOLS_PT_SetupDoorFlags,
    PDTOOLS_PT_SetupDoorSound,
    PDTOOLS_PT_SetupTintedGlass,
    PDTOOLS_PT_SetupLift,
    PDTOOLS_PT_SetupWaypoint,
    PD_SETUPLIFT_UL_interlinks,
    PD_SETUPWAYPOINT_UL_neighbours,
]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)

    Scene.pdmodel_list = CollectionProperty(type=PDModelListItem)
    Scene.pdmodel_listindex = IntProperty(name="ModelList item index", default=0)
    Scene.rompath = StringProperty(name="ROM file path", default='')

def unregister():
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)

    del Scene.pdmodel_list
    del Scene.pdmodel_listindex
    del Scene.rompath

if __name__ == '__main__':
    register()
